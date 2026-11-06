# 小米平板 7 Pro（muyu）Bootloader 解锁记录

本项目记录一台小米平板 7 Pro 从 Bootloader 锁定到解锁成功的实机探索，供研究相同机型的用户参考。后续目标是探索 Linux，但目前**没有刷入 Linux，也没有完成永久 Root**。

## 已验证的结果

- 机型：Xiaomi Pad 7 Pro，代号 `muyu`，型号 `24091RPADC`。
- 当时的系统：`OS3.0.307.0.WOYCNXM`，Android 16。
- 实机解锁后，`fastboot getvar unlocked` 返回 `yes`；Android 属性 `ro.boot.flash.locked` 为 `0`，`ro.boot.verifiedbootstate` 为 `orange`。
- 设备曾在分区修复后重新进入 Android。Root 和 Linux 尚未完成，不应将解锁状态当作 Root 成功。

## 使用的工具与流程概览

本次参考了第三方 [Mi8sG3orMi7pG3-Unlocker v3.0.0](https://github.com/Linuxoid-cn/Mi8sG3orMi7pG3-Unlocker/releases/tag/v3.0.0)。该版本的自动脚本菜单包含 **Xiaomi Pad 7 Pro**。工具及其脚本由原作者维护，本仓库不是原项目，也不附带其二进制文件。

已检查的脚本大致通过 ADB 推送 exploit 和辅助程序、尝试临时获取 root、改写 ABL，随后进入 Fastboot、临时改写 GPT、启动镜像并恢复 GPT，最后检查解锁状态。工具中的检查还涉及 FRP 分区操作，不能把它当作只读检测。请自行阅读原作者说明与脚本，确认设备、系统兼容性及工具来源。

**重要：本次成功并非可以声称直接照搬原脚本的一键流程。**实机过程曾遇到系统版本兼容和分区异常，使用过针对当前内核调整的临时程序，并进行过 ABL/GPT 备份、恢复及数据分区修复。当前仓库没有足够完整的命令日志和可独立验证的补丁来复现这些改动，因此暂不提供声称可逐步复现的命令，也不能保证其他版本或其他设备成功。请勿仅凭概览手动改写 ABL 或 GPT。

## 操作前与成功后检查

解锁和修复过程可能清空全部数据，也可能导致无法启动或需要专业维修。事先保存个人数据、设备原始分区备份和适用的官方恢复材料，并确认能够登录原绑定的小米账号；清空数据后可能要求账号激活。不要公开上传含设备标识或个人信息的备份与日志。

在 Fastboot 中，可用以下**只读**命令确认连接、设备代号和解锁状态：

```text
fastboot devices
fastboot getvar product
fastboot getvar unlocked
```

对这台设备，已记录的结果为 `product: muyu` 和 `unlocked: yes`。不同设备可能不支持相同变量或使用不同输出；应以实际输出为准。Android 启动并授权 USB 调试后，也可用以下命令辅助确认：

```text
adb shell getprop ro.boot.flash.locked
adb shell getprop ro.boot.verifiedbootstate
```

本次分别观察到 `0` 和 `orange`。解锁不等于永久 Root 或成功安装其他系统；修改系统后不要贸然重新锁定 Bootloader。

## 原厂 init_boot 提取实验

本仓库还包含 `extract_muyu_init_boot.py`，用于从指定 `OS3.0.307.0.WOYCNXM` OTA 中按 HTTP Range 提取 `init_boot.img`。该镜像用于后续 Root 研究，**不是解锁工具**。脚本依赖 Python 3.10+ 和 `requests`，采用固定版本的偏移和哈希，不适用于其他版本。

```powershell
python extract_muyu_init_boot.py --output H:\muyu-unlock\init_boot-extracted.img
```

选择不存在的输出路径。已在 Windows 上完成在线提取，结果为 8,388,608 字节，SHA-256 为：

```text
9dd01ed3e7e2097ea324f2a0fe75bc17fbe8ba2609973c6f1c17048dafe6c1a6
```

该哈希与所用 OTA 清单一致，但脚本不验证 OTA 数字签名。固件服务器不可用或不支持范围请求时，提取会失败；刷写前仍需独立核对机型、版本和文件来源。

## 交流与贡献

欢迎同机型用户通过 GitHub Issues 分享系统版本、所用工具版本、操作结果和已脱敏的错误信息，帮助核实兼容性及补全可复现步骤。请勿公开设备序列号、小米账号、激活码、分区备份或完整设备日志；未经验证的修复方法请标明状态。

## 后续计划

1. 在能够核实原始日志和改动的前提下，补充完整的可复现解锁记录及恢复步骤。
2. 完成 Magisk 补丁、刷写与 Root 实机验证。
3. 调研 `muyu` 的 Linux 启动链、内核、设备树和硬件驱动支持。

本项目不包含第三方固件、解锁工具、设备备份或账号数据。第三方项目的版权与许可归其各自作者所有。
