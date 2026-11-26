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
    client.get(BASE_URL + "/auth/login", timeout=20)

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
        timeout=20,
    )
    try:
        login_result = resp.json()
    except ValueError:
        return usr + " " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + " ❌ 登录失败：返回内容不是 JSON"
    if str(login_result.get("ret", "")).strip() != "1":
        return usr + " " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + " ❌ 登录失败：" + str(login_result.get("msg", resp.text))

    # 3. 签到（接口未变：POST /user/checkin）
    resp = client.post(
        BASE_URL + "/user/checkin",
        headers={
            "Referer": BASE_URL + "/user",
            "X-Requested-With": "XMLHttpRequest",
        },
        timeout=20,
    )
    try:
        checkin_result = resp.json()
    except ValueError:
        return usr + " " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + " ❌ 签到失败：返回内容不是 JSON"

    checkin_msg = str(checkin_result.get("msg", ""))
    if str(checkin_result.get("ret", "")).strip() == "1":
        msg = "✅ " + (checkin_msg if checkin_msg else "签到成功")
    elif ("签" in checkin_msg and "已" in checkin_msg) or "已签到" in checkin_msg:
        msg = "🟢 " + (checkin_msg if checkin_msg else "今日已签到")
    else:
        msg = "❌ 签到失败：" + (checkin_msg if checkin_msg else str(resp.text))

    # 4. 从用户中心页面获取当前流量信息（签到已过/失败时也能拿到）
    time.sleep(1)  # 稍等片刻，让登录会话在服务端稳定下来
    info = fetch_user_info(client, usr)
    extra = ""
    if info:
        extra = "，剩余流量：" + info.get("剩余流量", "?") + "，今日已用：" + info.get("今日已用", "?")
    return usr + " " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + " " + msg + extra


def fetch_user_info(client, usr=""):
    """登录后读取用户中心页面的账号流量信息（带重试）。

    原来只抓一次、正则又写死成 <a> 标签，遇到服务端限流或页面结构变化
    就整段拿不到，导致邮件里第二、三个账号没有流量字段。这里改为：
    1) 多个正则兜底；2) 抓不到就重试几次；3) 失败时打印诊断，便于排查。
    """
    info = {}
    for attempt in range(1, 4):  # 最多抓 3 次
        try:
            resp = client.get(BASE_URL + "/user", timeout=20)
            html = resp.text

            # 剩余流量：优先 id="remain"，再兜底找中文标签后紧跟的流量数字
            m = re.search(r'id="remain"[^>]*>([^<]+)<', html)
            if not m:
                m = re.search(r'剩余流量[^0-9]{0,40}?([0-9]+\.?[0-9]*\s*[KMGT]?B)', html, re.I)
            if m:
                info["剩余流量"] = m.group(1).strip()

            # 今日已用：不写死 <a> 标签，兼容任意标签或纯文本
            m = re.search(r'今日已用[^:：]*[:：]?\s*<[^>]*>\s*([^<]+)<', html)
            if not m:
                m = re.search(r'今日已用[^0-9]{0,40}?([0-9]+\.?[0-9]*\s*[KMGT]?B)', html, re.I)
            if m:
                info["今日已用"] = m.group(1).strip()

            if info.get("剩余流量") and info.get("今日已用"):
                return info

            # 没抓全，打印诊断（只进 Actions 运行日志，不进邮件正文）
            # 注意：Python 3.10/3.11 的 f-string 表达式里不能出现反斜杠，
            # 所以把带引号的判断先在表达式外算好，避免 \" 这类转义引发 SyntaxError。
            has_remain = 'id="remain"' in html
            has_used = "今日已用" in html
            print(f"[诊断] {mask_email(usr)} 第{attempt}次抓用户中心页未拿全流量："
                  f"HTTP {resp.status_code}，HTML {len(html)} 字符，"
                  f"含 id=remain: {has_remain}，"
                  f"含 今日已用: {has_used}")
        except Exception as e:
            print(f"[诊断] {mask_email(usr)} 第{attempt}次抓用户中心页异常：{e}")

        if attempt < 3:
            time.sleep(2)  # 等 2 秒再试，避开限流窗口

    # 三次都没拿全：有多少返回多少，缺失的由调用方补 "?"
    return info


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
    except Exception:  # 只发送文字
        content = MIMEText('%s' % info, 'plain', 'utf-8')
        message.attach(content)

    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465, timeout=20)
        server.login(sender, key)
        server.sendmail(sender, receivers, message.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"[邮件] 发送失败：{e}")
        return False


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
    for idx, (usr, pw) in enumerate(zip(user_list, pwd_list)):
        if idx > 0:
            time.sleep(3)  # 账号之间间隔 3 秒，降低连续请求触发限流的概率
        try:
            result = main(usr, pw)
        except Exception as e:
            result = usr + ' ' + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ' ❌ 签到异常：' + str(e)
        logging.info(mask_email(result))   # 写入 run.log（邮箱已脱敏）
        print(mask_email(result))          # 控制台输出也脱敏，避免账号出现在 Actions 日志
        results.append(result)

    # 所有账号签到完成后，统一发送一封汇总邮件
    info = '\n'.join(results)
    now = time.strftime("%Y-%m-%d %H:%M", time.localtime())
    has_fail = any('❌' in r for r in results)
    status = '部分失败' if has_fail else '全部成功'
    subject = f'【V2free签到】{now} {status}（{len(results)}个账号）'
    sent = send(info=info, mail=[args.semail, args.secode], receivers=args.remail, subject=subject)
    if sent:
        print(f'汇总邮件已发送（共 {len(results)} 个账号）')
    else:
        print(f'汇总邮件发送失败（共 {len(results)} 个账号）')
