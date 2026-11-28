#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
任务名称
name: V2free 自动签到（邮件通知 + 日志归档）
定时规则（青龙服务器为 Asia/Shanghai，按北京时间填三条）
cron: 7 7 * * *
cron: 7 11 * * *
cron: 7 15 * * *

用法：python3 /ql/scripts/v2free_qinglong.py
依赖：pip3 install requests

环境变量（青龙 环境变量 页面添加）：
  V2_USER  必填  签到账号，多个用半角逗号分隔；兼容 USER
  V2_PWD   必填  对应密码，顺序与账号一一对应；兼容 PWD
  V2_REMAIL 必填 收件邮箱；兼容 remail
  V2_SEMAIL 必填 发件邮箱（默认 QQ 邮箱）；兼容 semail
  V2_SECODE 必填 发件邮箱 SMTP 授权码，不是登录密码；兼容 secode
  V2_SMTP_HOST / V2_SMTP_PORT  可选，默认 smtp.qq.com / 465
  V2_MAIL_IMAGE  可选，邮件正文附加的图片路径
  V2FREE_LOG_PATH  可选，日志路径，默认 /ql/data/scripts/v2free_run.log
  V2FREE_GIT_REPO  可选，本地 git 仓库目录；设置后才启用日志 git 提交推送
  V2FREE_INTERVAL  可选，账号间隔秒数，默认 3
  V2FREE_QINGLONG_NOTIFY  可选，设为 1 时同时发一份青龙通知
  V2FREE_FAIL_EXIT  可选，默认 1；有失败账号时退出码为 1
"""
