from jenkinsapi.jenkins import Jenkins
import sys


def jenkins_login(jenkins_path, key, token):
    return Jenkins(jenkins_path, key, token)


jenkins = jenkins_login("http://127.0.0.1:8080", "sakura", "zenjoy2019")

last_good_build_number = jenkins[sys.argv[1]].get_last_good_buildnumber()

print(last_good_build_number)