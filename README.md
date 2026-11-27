# V2free 自动签到 · 邮件通知 · 日志归档

V2free auto check-in with email notification and auto-committed run.log

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)](https://www.python.org/)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-enabled-2088FF?logo=github-actions&logoColor=white)](https://github.com/features/actions)
[![Schedule](https://img.shields.io/badge/定时-07%3A07%20%2F%2011%3A07%20%2F%2015%3A07-orange)](https://github.com/features/actions)

基于 GitHub Actions 的 V2free 自动签到方案：定时签到、邮件通知，签到结果自动写入 `run.log` 并归档到仓库。

---

## 功能特性

- 支持**多账号**批量签到，账号与密码用半角逗号分隔
- 每天 **07:07 / 11:07 / 15:07**（北京时间）自动运行，也可随时手动触发
- 每次运行发送**邮件通知**，展示签到结果与剩余流量
- 签到结果写入 `run.log` 并**自动提交回仓库**，邮箱脱敏，可长期追溯
- 提交信息自动标注 `⭐ 签到成功` 或 `❌ 签到失败`，一目了然
- 内置 `concurrency` 并发锁，避免多次触发导致日志提交冲突

## 快速开始

1. 点击仓库右上角 **Fork** 按钮，将项目 Fork 到自己的账号下。
2. 进入你 Fork 后的仓库，依次点击 **Settings → Secrets and variables → Actions → New repository secret**。
3. 按下表添加 5 个 Secret（变量名区分大小写，必须完全一致）。
4. 在 **Actions** 页面点 **Run workflow** 手动跑一次验证；确认无误后，定时任务会自动运行。

## 参数配置

| Secret | 示例值 | 说明 |
| --- | --- | --- |
| `USER` | `123@qq.com,567@outlook.com` | 签到账号，多个用半角逗号分隔 |
| `PWD` | `ccc,aaa` | 对应账号密码，顺序与 `USER` 一一对应 |
| `remail` | `abc@163.com` | 收件邮箱 |
| `semail` | `cdc@163.com` | 发件邮箱（QQ 邮箱） |
| `secode` | `xxxxxxxxxxxxxx` | 发件邮箱的 **SMTP 授权码**，不是登录密码 |

## 运行机制

**定时执行**：workflow 中 cron 为 `7 7`、`7 11`、`7 15`，并指定 `timezone: Asia/Shanghai`，对应北京时间 **07:07、11:07、15:07**。GitHub 定时任务在高负载时可能延迟几分钟到几十分钟，甚至偶尔丢弃，属平台现象；手动触发（Run workflow）无延迟。请在两次运行之间留足间隔，避免站点限流。

**邮件通知**：`main.py` 的 `send()` 通过 QQ 邮箱 SMTP（`smtp.qq.com:465`，SSL）发送，每次运行都发一封。`secode` 填登录密码会发送失败，必须用授权码。

**日志归档**：脚本用 `logging` 把结果写入 `run.log`（邮箱脱敏为 `1****@qq.com`），工作流随后 `git add -f` 并提交回仓库。提交信息根据本次结果动态显示 `⭐ 签到成功` 或 `❌ 签到失败`。

**防并发**：顶层 `concurrency` 配置保证同一时间只有一个运行，`queue: max` 让排队的运行不会被后来者取消。

**健壮性**：签到任务设置了 `timeout-minutes: 15`，所有网络请求带超时，工作流时区为 `Asia/Shanghai`，因此 `run.log` 和邮件里的时间都是北京时间；邮件发送失败会明确打印失败提示，不再误报成功。

## 签到状态

| 日志 / 邮件中的显示 | 含义 |
| --- | --- |
| `✅ 签到成功` | 本次签到成功 |
| `🟢 您似乎已经签到过了...` | 今日已签到过（站点返回原文） |
| `❌ 签到失败：原因` | 签到失败，如"请求过于频繁，请稍后再试" |

三种状态末尾均附带当前流量：`剩余流量：***GB，今日已用：***GB`。

---

<a id="donate"></a>
## ☕ 支持与投喂：微信与支付宝赞赏码

脚本完全免费，赞赏纯自愿，不影响任何功能。

<p align="center">
  <img src="assets/donate-wechat.png" width="260" alt="微信赞赏码" />
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <img src="assets/donate-alipay.jpg" width="260" alt="支付宝收款码" />
</p>

<p align="center"><sub>微信支付（左）      ·      支付宝（右）</sub></p>

> [!WARNING]
> 收款码仅用于向作者自愿赞赏。任何第三方以代下载、代部署、内部资源、会员群或官方授权为由收费，均与作者无关。

## 注意事项

- 账号与密码的个数必须一致，否则脚本会报错退出。
- `secrets` 中的密码和授权码属于敏感信息，请勿写入代码或日志，也不要把私有配置提交到公开仓库。
- 日志中的邮箱已脱敏，但邮件正文中是完整账号，请注意邮件的使用范围。
- 如果这个项目帮你省下了一点时间，欢迎点个 ⭐。
