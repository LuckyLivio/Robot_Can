# 跨设备取用与压缩包区别

## 已有仓库的取用方式

分类入口与论文写作材料同步到同一个 GitHub 仓库；新设备可克隆，已有克隆可拉取：

```powershell
git clone https://github.com/LuckyLivio/Robot_can.git
Set-Location Robot_can
```

或在已有仓库中执行 `git pull`，随后打开 `PROJECT_NAVIGATION.md`、`WORKSPACE/index.html` 或 `THESIS_HANDOFF_20261015/index.html`。

GitHub 的迁移目录采用写作版：不重复上传 652 份 gzip 日志。完整原 JSONL 已在同一仓库的 `reproduction/` 原路径中，保留其原始 Git 历史。文档、表、图、数据、权重与非 JSONL 冻结快照都在迁移目录内。仓库里的迁移目录用 `verify_package.py --mode writing` 核对；若要逐步核查原日志，按 `SOURCE_ASSETS.csv` 的 source_repo_path 在仓库原路径取用。

来源基线为提交 `c8bbe86d0bd760524afb946a2c9220641a0872f0`。这是原实验资产版本；后续目录/写作交接提交不是新增实验。`full_verification.json` 记录整理设备曾对完整版所有压缩日志逐一解压并比对原始 SHA，并不表示写作版包含 gzip 正文。

## 本地压缩包

- `THESIS_HANDOFF_20261015_FULL.zip`：完整独立归档，包含 `08_full_traces_gzip`；复制到任意设备无需从 GitHub 补日志。文件夹解压后约 1.9 GiB。
- `THESIS_HANDOFF_20261015_WRITING.zip`：只省略上述压缩步骤日志，体积较小；全部表、图、逐回合结果、模型权重和数据均保留，可独立完成现有证据支持的正文写作。
- 同名 `.sha256` 文件用于传输后比对 ZIP 的完整 SHA-256。压缩包不包含虚拟环境。

Windows 校对文件哈希：

```powershell
Get-FileHash -Algorithm SHA256 .\THESIS_HANDOFF_20261015_WRITING.zip
```

与同名 `.sha256` 文本中的值比较。解压后校验：

```powershell
Set-Location .\THESIS_HANDOFF_20261015
python .\09_tools\verify_package.py --mode writing
```

完整版可使用 `--mode full`；这只读取与解压现有文件流，不执行仿真、训练或策略。

## 写作前最后核对

1. 使用新修订提纲，不把根目录旧版当成唯一事实来源。
2. 每张图/表保持本包 catalog 的指标、分母、种子和起点批次。
3. 学校模板、题目与导师要求仍待确认；已有八条文献不是完整综述。
4. 不为写作运行旧仿真验证入口，也不在已知确认集上选新参数。
