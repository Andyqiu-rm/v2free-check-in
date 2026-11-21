import requests
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
import time
import argparse
import logging


BASE_URL = "https://w1.v2ai.top"  # 新版登录/签到域名

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


# 邮箱脱敏：150623855@qq.com -> 1****@qq.com
def mask_email(text):
    return re.sub(r'[\w.+-]+@[\w.-]+\.\w+',
                  lambda m: m.group(0)[0] + '****' + m.group(0)[m.group(0).rfind('@'):],
                  text)


def main(usr, pw):
    """签到单个账号，返回一行结果字符串（不发邮件）"""
    client = requests.Session()
    client.headers.update({"User-Agent": UA})

    # 1. 访问登录页，获取初始 Cookie
    client.get(BASE_URL + "/auth/login")

    # 2. 登录（新版表单字段：email/passwd/code/agree/remember_me）
    login_data = {
        "email": usr,
        "passwd": pw,
        "code": "",
        "agree": "1",       # 新版登录必须携带 agree=1
        "remember_me": "",
    }
    resp = client.post(
        BASE_URL + "/auth/login",
        data=login_data,
        headers={
            "Referer": BASE_URL + "/auth/login",
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    try:
        login_result = resp.json()
    except ValueError:
        return usr + " " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + " ❌ 登录失败：返回内容不是 JSON"
    if login_result.get("ret") != 1:
        return usr + " " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + " ❌ 登录失败：" + str(login_result.get("msg", resp.text))

    # 3. 签到（接口未变：POST /user/checkin）
    resp = client.post(
        BASE_URL + "/user/checkin",
        headers={
            "Referer": BASE_URL + "/user",
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    try:
        checkin_result = resp.json()
    except ValueError:
        return usr + " " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + " ❌ 签到失败：返回内容不是 JSON"

    checkin_msg = str(checkin_result.get("msg", ""))
    if checkin_result.get("ret") == 1:
        msg = "✅ " + (checkin_msg if checkin_msg else "签到成功")
    elif ("签" in checkin_msg and "已" in checkin_msg) or "已签到" in checkin_msg:
        msg = "🟢 " + (checkin_msg if checkin_msg else "今日已签到")
    else:
        msg = "❌ 签到失败：" + (checkin_msg if checkin_msg else str(resp.text))

    # 4. 从用户中心页面获取当前流量信息（签到已过/失败时也能拿到）
    info = fetch_user_info(client)
    extra = ""
    if info:
        extra = "，剩余流量：" + info.get("剩余流量", "?") + "，今日已用：" + info.get("今日已用", "?")
    return usr + " " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + " " + msg + extra


def fetch_user_info(client):
    """登录后读取用户中心页面的账号流量信息"""
    try:
        html = client.get(BASE_URL + "/user").text
        info = {}
        m = re.search(r'id="remain"[^>]*>([^<]+)<', html)
        if m:
            info["剩余流量"] = m.group(1).strip()
        m = re.search(r'今日已用:\s*<a[^>]*>([^<]+)<', html)
        if m:
            info["今日已用"] = m.group(1).strip()
        return info
    except Exception:
        return {}


# 发送汇总邮件：所有账号的结果放在一封邮件里
def send(info, mail, receivers, subject='', imgpth=''):
    sender, key = mail
    message = MIMEMultipart('mixed')
    if subject == "": subject = info
    message['Subject'] = subject
    message['From'] = sender
    message['To'] = receivers
    try:  # 尝试发送图片和文字
        fp = open(imgpth, 'rb')  # 打开文件
        msgImage = MIMEImage(fp.read())  # 创建MIMEImage对象，读取图片内容并作为参数
        fp.close()  # 关闭文件
        msgImage.add_header('Content-ID', '<image1>')  # 指定图片文件的Content-ID，imgid，<img>标签中的src用到
        html_img = f'<p>{info}<br><img src="cid:image1"></br></p>'  # html格式添加图片
        message.attach(msgImage)
        message.attach(MIMEText(html_img, 'html', 'utf-8'))  # 添加到邮件正文
    except:  # 只发送文字
        content = MIMEText('%s' % info, 'plain', 'utf-8')
        message.attach(content)

    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(sender, key)
        server.sendmail(sender, receivers, message.as_string())
        server.quit()
        # print("send OK")
    except smtplib.SMTPException as e:
        print(e)


if __name__ == "__main__":
    LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
    logging.basicConfig(
        filename='run.log',
        level=logging.INFO,
        format=LOG_FORMAT,
        encoding='utf-8'
    )

    parser = argparse.ArgumentParser(description='V2free签到脚本（所有账号汇总为一封邮件）')
    parser.add_argument('--usernames', type=str, help='账号，多个用英文逗号分隔')
    parser.add_argument('--passwords', type=str, help='密码，多个用英文逗号分隔，顺序与账号对应')
    parser.add_argument('--remail', type=str, help='接收邮箱')
    parser.add_argument('--semail', type=str, help='发送邮箱')
    parser.add_argument('--secode', type=str, help='发送密码')
    args = parser.parse_args()

    # 兼容旧的 --username/--password 单账号参数
    usernames = args.usernames if args.usernames else ''
    passwords = args.passwords if args.passwords else ''
    user_list = [u.strip() for u in usernames.split(',') if u.strip()]
    pwd_list = [p.strip() for p in passwords.split(',') if p.strip()]

    if len(user_list) == 0 or len(user_list) != len(pwd_list):
        print('账号为空，或账号与密码个数不对应')
        raise SystemExit(1)

    print(f'共有 {len(user_list)} 个账号，开始签到')

    # 逐个签到，收集所有结果，不逐个发邮件
    results = []
    for usr, pw in zip(user_list, pwd_list):
        try:
            result = main(usr, pw)
        except Exception as e:
            result = usr + ' ' + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ' ❌ 签到异常：' + str(e)
        logging.info(mask_email(result))   # 写入 run.log（邮箱已脱敏）
        print(result)
        results.append(result)

    # 所有账号签到完成后，统一发送一封汇总邮件
    info = '\n'.join(results)
    now = time.strftime("%Y-%m-%d %H:%M", time.localtime())
    has_fail = any('❌' in r for r in results)
    status = '部分失败' if has_fail else '全部成功'
    subject = f'【V2free签到】{now} {status}（{len(results)}个账号）'
    send(info=info, mail=[args.semail, args.secode], receivers=args.remail, subject=subject)
    print(f'汇总邮件已发送（共 {len(results)} 个账号）')
