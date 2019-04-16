#!/usr/bin/env python3
"""
勾搭jenkins，获取打包的changes里被程序标记的bugid，并自动标修jira上的这些bug到可验的状态
"""
import jenkinsapi
from jenkinsapi.jenkins import Jenkins
from jira import JIRA
import re
import sys
import json
from pprint import pprint





def jenkins_login(jenkins_path, key, token):
    return Jenkins(jenkins_path, key, token)


def find_bugs(comment_str: str, project_code: str):
    """
    从changes里找出修复的bugid，输出一个bugid的列表
    :param comment_str:
    :return:
    """
    target_str = project_code + "-[1-9][0-9]*"  # bugid的正则表达式
    bugid_parttern = re.compile(target_str, re.I)  # 从comment里找出bugid，不区分大小写
    bugid_list = bugid_parttern.findall(comment_str)
    return bugid_list


def get_last_good_build(jenkins, job_name):
    """
    收集最后一次成功出包的信息
    :param jenkins:
    :param job_name:
    :return:
    """
    last_good_build_number = jenkins[job_name].get_last_good_buildnumber()
    last_good_build_info = {}
    last_good_build = jenkins[job_name].get_build(last_good_build_number)
    last_good_build_info["build_url"] = last_good_build.get_build_url()
    last_good_build_info["build_number"] = last_good_build_number
    last_good_build_info.update(last_good_build.get_params())
    return last_good_build_info


def collect_bug_fix(jenkins, project_info):
    """
    收集自最近一次成功出包后，到这次之间的所有提交记录,以及这次出包的信息
    提取出包含bugid的提交，整理成需要的格式，以供修改jira上的bug表时填入comment
    :param jenkins:
    :param project_info:
    :return: 以bugid为key,要修改的bug comment为value的字典,以及一个包含所有提交id的列表
    """
    job_name = project_info["job_name"]
    project_code = project_info["project_code"]
    this_build_number = project_info["this_build_number"]
    builds_dict = jenkins[job_name].get_build_dict()  # 获取这个工程的所有build信息
    last_good_build_info = get_last_good_build(jenkins, job_name)
    # 获取最近一次成功打包的详细信息
    last_good_build_number = last_good_build_info["build_number"] #最新的包的打包号
    # 以下是收集自上次跑脚本的版本后，到最近一次成功出包之间的所有提交记录
    bugfix_list = []
    commit_list = []
    for build_number in builds_dict.keys():
        # 遍历所有build_number,只要在上次成功构建之后到这次成功打包之间的build_number
        if int(last_good_build_number) < int(build_number) <= int(this_build_number):
            single_build = jenkins[job_name].get_build(build_number)
            changeset = single_build.get_changeset_items()  # 提取有效build的提交记录
            for change in changeset:
                commit_list.append(change["id"])
                # 遍历提交记录，只取包含bugid的提交记录，并整理出将来标修这个bug时要写的comment
                bugid_list = find_bugs(change["comment"], project_code)
                if bugid_list:
                    bug_comment = "FixBy: %s\nCommitId: %s\nComment: %s\nFixVersion: %d" % (
                        change["author"]["fullName"],
                        change["id"],
                        change["comment"],
                        this_build_number
                    )
                    for bugid in bugid_list:
                        bugfix_dict = dict()
                        # 把每条bug都单独列一个comment，哪怕是同一个提交
                        bug_id = bugid.upper()  # 把bugid大写
                        bugfix_dict["id"] = bug_id
                        bugfix_dict["comment"] = bug_comment
                        bugfix_dict["assignee"] = {"name": change["author"]["fullName"]}
                        bugid_list.append(bugfix_dict)
    # 整理输出字典的内容，把后面需要的变量统统都塞进去：
    bugfix_data = {"bugfix": bugfix_list}
    bugfix_data["project_code"] = project_code
    bugfix_data["commit_list"] = commit_list
    bugfix_data["env"] = project_info["build_env"]
    bugfix_data["platform"] = project_info["platform"]
    bugfix_data["version_name"] = project_info["build_env"] + "#" + this_build_number
    return bugfix_data


def get_project_info(job_name, this_build_number):
    """
    获取项目信息，从命令行参数获取jenkins的job名字，和当前打包的版本号，
    猜测项目代号, 平台和环境
    :param job_name:
    :param this_build_number:
    :return:
    """
    # 初始化输出字典格式：
    project_info = {
        "project_code": "WCI",
        "build_env": "Beta",
        "job_name": job_name,
        "platform": "Android",
        "this_build_number": this_build_number
    }
    # 识别项目的开发环境：
    if job_name.find("Beta") != -1:
        project_info["build_env"] = "Beta"
    elif job_name.find("Alpha") != -1:
        project_info["build_env"] = "Alpha"
    else:
        print("未定义的版本环境")
        project_info["build_env"] = "Build"
    # 识别项目的id：
    if job_name.find("word5") != -1:
        project_info["project_code"] = "PDM"  # 从job name识别wordv5项目
    elif job_name.find("Word") != -1 and job_name.find("V4") != -1:
        project_info["project_code"] = "WGD"  # 从job name识别wordv4项目
    elif job_name.find("Word") != -1 and job_name.find("V1") != -1:
        project_info["project_code"] = "WCI"  # 从job name 识别wordv1项目
    elif job_name.find("WordCross") != -1:
        project_info["project_code"] = "WCE"  # 从job name 识别word cross EN项目
    elif job_name.find("TestProject") != -1:
        project_info["project_code"] = "TP"  # 从job name 识别测试专用项目
    else:
        print("未能识别项目，脚本终止")
        return
    # 识别项目的平台：
    if job_name.find("iOS") != -1:
        project_info["platform"] = "iOS"
    elif job_name.find("Web") != -1:
        project_info["platform"] = "Web"
    elif job_name.find("Android") != -1:
        project_info["platform"] = "Android"
    elif job_name.find("Android") != -1:
        project_info["platform"] = "Server"
    else:
        print("未能识别项目平台，脚本终止")
    return project_info


def jira_login():
    return JIRA(server="http://10.7.0.7:8080", basic_auth=("jenkins", "JJ1941"))


def update_version(jira_obj, bugfix_data):
    """
    获取指定项目的所有版本号并遍历，检查要添加的版本号是否已经存在，如果存在，则记录该版本的id，
    如果不存在则创建之，并返回版本id
    :param jira_obj:
    :param bugfix_data:
    :return: 返回一个版本id
    """
    project_code = bugfix_data["project_code"]
    # 下面检查新版本是否已经在jira上创建过
    versions = jira_obj.project_versions(project_code)
    latest_version_id = ""
    for single_version in versions:
        if single_version.name == bugfix_data["version_name"]:
            latest_version_id = single_version.id
            print("该版本在jira上已经存在，无需创建！版本id：", latest_version_id)
            break
    if not latest_version_id:  # 若没创建过，则创建该版本并返回版本id
        latest_version_id = jira_obj.create_version(
            bugfix_data["version_name"],
            project_code,
            description="Created by Jenkins",
            released=True
        ).id
    return latest_version_id


def build_bugs(jira_obj, param_dict, platform, env):
    """
    把resolved状态的bug的状态改为built，并且添加 fix version，comment， assignee等信息
    :param jira_obj:
    :param param_dict: 标修bug的同时要修改的bug 字段,是个字典, 样子应该是这样的：
        {
            "fixVersions": [{"name": "beta#193"}],
            "assignee": {"name": "lichailin"}
        }
    :return:
    """
    # 先检查该bug是否处于等待build的状态：
    if not jira_obj.transitions(param_dict["id"], "71"):
        print("BugId为%s的bug无法被'Build'" % param_dict["id"])
        return False
    # 获取该bug实例
    Bug = jira_obj.issue(param_dict["id"])
    # 检查该bug的label里的平台的信息，若限制了设备平台的bug的label里没有当前工程的平台信息则不应该被标修：
    if (platform not in Bug.fields.labels) and ("iOS" in Bug.fields.labels or
                                         "Android" in Bug.fields.labels or
                                         "Web" in Bug.fields.labels or
                                         "Server" in Bug.fields.labels):
        print("BugId为%s的bug因为平台限制而不会被'Build'" % param_dict["id"])
        return False
    # 检查该bug的label里的测试环境的信息，若限制了测试环境的bug的label里没有当前工程的env则不应该被标修
    if (env not in Bug.fields.labels) and ("Alpha" in Bug.fields.labels or
                                         "Beta" in Bug.fields.labels or
                                         "Production" in Bug.fields.labels or
                                         "Distribution" in Bug.fields.labels):
        print("BugId为%s的bug因为测试环境限制而不会被'Build'" % param_dict["id"])
        return False
    # 构建要修改的field字典
    bug_dict = {"assignee": {"name": param_dict["assignee"]}}
    bug_dict["fixVersions"] = [{"name": param_dict["version"]}]
    # 触发"71"号操作，Build
    jira_obj.transition_issue(param_dict["id"], "71", param_dict)
    # 更新bug的指派，标修版本等字段
    Bug.update(fields=bug_dict)
    # 更新bug的备注信息
    jira_obj.add_comment(Bug, param_dict["comment"])
    return True


def update_bugs(jira_obj, bugfix_data):
    """
    连续标修bug
    :param jira_obj:
    :param bugfix_data:
    :return:
    """
    fixed_list = []
    if not bugfix_data["bugfix"]:
        print("这个版本的提交里没有标修任何bug，跳过第一次标修")
    else:
        for bug_dict in bugfix_data["bugfix"]:
            bug_dict["version"] = bugfix_data["version_name"]  # 给bug字典增加了一个标修版本的字段
            result = build_bugs(jira_obj, bug_dict, bugfix_data["platform"], bugfix_data["env"])
            if result:
                fixed_list.append(bug_dict["id"])

    return fixed_list


def main():
    this_job_name = sys.argv[1]
    this_build_number = sys.argv[2]
    #this_job_name = "TestProject_Auto_Alpha_Client_Android"
    #this_build_number = "3"
    jenkins_type = "yifang.local"  # 设定jenkins运行方式
    jenkins_paths = {"old": {"url": "http://10.7.0.5:8080",
                             "key": "chailin.li",
                             "token": "1119f4e57cfc32d6733c6b947a49af907b"},
                     "new": {"url": "http://10.7.0.8:8080",
                             "key": "chailin.li",
                             "token": "1136c5fdf1c94550cdb885762ea9e83058"},
                     "my": {"url": "http://58.87.67.171:8080",
                            "key": "chairolling",
                            "token": "11b0f557fd24ad8a2c0f1f780bcda2e33c"},
                     "yifang.local": {"url": "http://127.0.0.1:8080",
                                      "key": "sakura",
                                      "token": "zenjoy2019"}
                     }
    project_info = get_project_info(this_job_name, this_build_number)
    if not project_info:
        raise ValueError("Unsupported Project!", this_job_name)
    jenkins_object = jenkins_login(jenkins_paths[jenkins_type]["url"],
                                   jenkins_paths[jenkins_type]["key"],
                                   jenkins_paths[jenkins_type]["token"]
                                   )
    bugfix_data = collect_bug_fix(jenkins_object, project_info)
    pprint(bugfix_data)
    jira_obj = jira_login()
    latest_version_id = update_version(jira_obj, bugfix_data)
    print(latest_version_id)
    if latest_version_id:
        fixed_bugs = update_bugs(jira_obj, bugfix_data)
        pprint(fixed_bugs)
    return




if __name__ == "__main__":
    main()