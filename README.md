# Xiaomi Pad 7 Pro Linux 探索

记录小米平板 7 Pro（代号 `muyu`）的解锁后检查、固件镜像提取和 Linux 移植探索。

## 当前进度

- Bootloader 曾通过 fastboot 和 Android 属性确认已解锁；Android 曾恢复启动。
- Root 尚未完成刷入和验证；Linux 尚未安装，硬件支持仍待调查。

本项目是实验记录，不能一键解锁或安装 Linux。错误刷写可能导致设备无法启动；请保留与系统版本匹配的原厂镜像和设备备份，不要在修改系统后重新锁定 Bootloader。

## 已验证的镜像提取

从 `OS3.0.307.0.WOYCNXM` 完整 OTA 按范围读取数据，重建 `init_boot.img`，大小 8,388,608 字节，SHA-256：

`9dd01ed3e7e2097ea324f2a0fe75bc17fbe8ba2609973c6f1c17048dafe6c1a6`

结果与 OTA 清单中的哈希一致；这一校验本身不能证明清单来源或签名。镜像与固件版本绑定，使用前必须核对机型和版本。

`extract_muyu_init_boot.py` 从固定版本的官方 OTA 按 HTTP Range 提取目标镜像，依赖 Python 3.10+ 和 `requests`。它校验 HTTP 响应范围、已知清单哈希、各数据块哈希及最终镜像哈希，不需要先下载完整 OTA。它使用该版本固定偏移和哈希，不适用于其他固件；也没有验证 OTA 的数字签名。

```powershell
python extract_muyu_init_boot.py --output H:\muyu-unlock\init_boot-extracted.img
```

请事先安装 `requests` 并选择尚不存在的输出路径。固件服务器必须支持范围请求；网络或服务器限制可能导致提取失败。脚本已在 Windows 上从官方 OTA 完成一次端到端网络提取，结果为 8,388,608 字节，SHA-256 与上方一致；也使用历史数据块完成过离线重建验证。

## 后续工作

1. 验证端到端网络提取，研究自动解析 ZIP 和 OTA 元数据以支持其他版本。
2. 完成 Magisk 补丁、刷写及 Root 实机验证。
3. 调查 Linux 的内核、设备树、启动链和硬件驱动支持。
4. 记录恢复步骤和实际验证结果。

## 参考

- [Magisk 官方安装说明](https://topjohnwu.github.io/Magisk/install.html)
- [Magisk 官方项目](https://github.com/topjohnwu/Magisk)
- [解锁工具项目](https://github.com/Linuxoid-cn/Mi8sG3orMi7pG3-Unlocker)

项目不包含第三方工具、固件、设备备份或账号数据；第三方软件权利和许可归各自作者所有。
