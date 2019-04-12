"""
勾搭jenkins，获取打包的changes里被程序标记的bugid，并自动标修jira上的这些bug到可验的状态
"""
import jenkinsapi
from jenkinsapi.jenkins import Jenkins
from jira import JIRA
import re
import sys
from pprint import pprint


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


def jenkins_login(jenkins_path, key, token):
    return Jenkins(jenkins_path, key, token)


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


def collect_bug_fix(jenkins, job_name, project_code, last_checkpoint=1):
    """
    收集自上次跑脚本的版本后，到最近一次成功出包之间的所有提交记录,以及最近一次成功出包的信息
    提取出包含bugid的提交，整理成需要的格式，以供修改jira上的bug表时填入comment
    :param jenkins:
    :param job_name:
    :param project_code:
    :param last_checkpoint:
    :return: 以bugid为key,要修改的bug comment为value的字典,以及一个包含所有提交id的列表
    """
    builds_dict = jenkins[job_name].get_build_dict()  # 获取这个工程的所有build信息
    last_good_build_info = get_last_good_build(jenkins, job_name)
    # 获取最近一次成功打包的详细信息
    last_good_build_number = last_good_build_info["build_number"] #最新的包的打包号
    # 以下是收集自上次跑脚本的版本后，到最近一次成功出包之间的所有提交记录
    bugfix_dict = {}
    commit_list = []
    for build_number in builds_dict.keys():
        # 遍历所有build_number,只要在上次检查之后到最新一次成功打包之间的build_number
        if last_checkpoint < int(build_number) <= last_good_build_number:
            single_build = jenkins[job_name].get_build(build_number)
            changeset = single_build.get_changeset_items()  # 提取有效build的提交记录
            for change in changeset:
                commit_list.append(change["id"])
                # 遍历提交记录，只取包含bugid的提价记录，并整理出将来标修这个bug时要写的comment
                bugid_list = find_bugs(change["comment"], project_code)
                if bugid_list:
                    bug_comment = "FixBy: %s\nCommitId: %s\nComment: %s\nFixVersion: %d\nBuildUrl: %s" % (
                        change["author"]["fullName"],
                        change["id"],
                        change["comment"],
                        last_good_build_number,
                        last_good_build_info["build_url"]
                    )
                    for bugid in bugid_list:
                        # 把每条bug都单独列一个comment，哪怕是同一个提交
                        bug_id = bugid.upper()  # 把bugid大写
                        bugfix_dict[bug_id] = bug_comment

    return last_good_build_number, bugfix_dict, commit_list


def main():
    jenkins_type = "yifang.local"
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
    job_name = sys.argv[1]
    if job_name.find("Beta") != -1:
        build_env = "Beta"
    elif job_name.find("Alpha") != -1:
        build_env = "Alpha"
    else:
        print("找不到打包环境")
        build_env = "Build"

    jenkins_object = jenkins_login(jenkins_paths[jenkins_type]["url"],
                                   jenkins_paths[jenkins_type]["key"],
                                   jenkins_paths[jenkins_type]["token"]
                                   )
    build_number, fixes, commits = collect_bug_fix(jenkins_object, job_name, "WCI", last_checkpoint=4)
    build_data = {"bugfix": fixes}
    build_data["commit_list"] = commits
    build_data["build_name"] = build_env + "#" + str(build_number)
    pprint(build_data)
    


if __name__ == "__main__":
    main()