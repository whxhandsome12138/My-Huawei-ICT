# 数据与论文：从 Release 下载，用哈希校验

KIMORE 数据集和论文草稿**不放进 Git 历史**，而是放在 GitHub Release 附件里：

**下载页 → https://github.com/whxhandsome12138/My-Huawei-ICT/releases/tag/data-v1.0**

| 文件 | 大小 | 用途 | 直链 |
| :-- | --: | :-- | :-- |
| `CG-….zip` | 1.81 GB | 健康组作者包（`CG/Expert`、`CG/NotExpert`，含作者 MATLAB 脚本与深度 AVI） | [下载](https://github.com/whxhandsome12138/My-Huawei-ICT/releases/download/data-v1.0/CG-20261123T070200Z-1-001.zip) |
| `GPP-….zip` | 1.67 GB | 患者组作者包（`BackPain` / `Stroke` / `Parkinson`） | [下载](https://github.com/whxhandsome12138/My-Huawei-ICT/releases/download/data-v1.0/GPP-20261123T070200Z-1-001.zip) |
| `archive.zip` | 178 MB | 精简包（只有骨架 + 标签，顶层 `Kimore/`），只要跑服务下载这个就够 | [下载](https://github.com/whxhandsome12138/My-Huawei-ICT/releases/download/data-v1.0/archive.zip) |
| `draftKIMORE.pdf` | 1.9 MB | 论文草稿（口径依据） | [下载](https://github.com/whxhandsome12138/My-Huawei-ICT/releases/download/data-v1.0/draftKIMORE.pdf) |
| `SHA256SUMS.txt` | 1 KB | 上面四个文件的哈希 | [下载](https://github.com/whxhandsome12138/My-Huawei-ICT/releases/download/data-v1.0/SHA256SUMS.txt) |

## 为什么是 Release，不是 `git add`

1. **Git 的单文件硬上限是 100 MB**。`CG` 1.81 GB、`GPP` 1.67 GB，进不了 Git 历史，`git push` 会被服务端直接拒收。
2. **Git LFS 免费额度只有 1 GB 存储 + 1 GB 月流量**，两个包合计 3.5 GB，不够。
3. **Release 附件单文件上限 2 GiB**，正好放得下，而且不污染 clone 体积、不占 LFS 配额。
4. 二进制放在 Release 还有一个好处：`git clone` 的人几秒钟拿到代码，需要数据的人再单独下载。

## 授权与使用范围

- 经数据集作者同意再分发（2026-11-27）。
- 仅用于科研与教学；引用请按论文：
  Capecci M, Ceravolo M G, Ferracuti F, et al. *The KIMORE dataset: KInematic assessment of
  MOvements and clinical scores for telerehabilitation of low back pain.* IEEE TNSRE, 2019, 27(7): 1436–1448.
- 论文草稿版权在 IEEE 与作者，随 Release 提供仅为便于核对口径，不构成对论文的再授权。
- 若权利人对本附件有异议，请在 Issues 提出，我们会立即移除。

## 校验（务必做一次）

```bash
sha256sum -c SHA256SUMS.txt            # Linux / macOS
python tools/check_data.py --root <放 zip 的目录>     # 跨平台：逐条报通过/缺失/大小不符/哈希不符
```

`check_data.py` 也支持 `--no-hash`（只比大小，几秒出结果）。

## 数据放哪

`mcp_server` 只需要一个能指到动作记录根目录的路径，两种摆法都行：

```text
# A. 精简包解开
<DATA_ROOT>/Kimore/<CG|GPP>/<组别>/<SID>/Es1..Es5/{Raw,Label}/...

# B. 作者包解开（多个顶层目录）
<DATA_ROOT>/CG/Expert/E_ID1/Es2/{Raw,Script,Label}/...
<DATA_ROOT>/GPP/BackPain/...
```

启动时指定：

```bash
python mcp_server/server.py --port 9100 --data-root /path/to/Kimore
```

## 不要提交回仓库

`.gitignore` 已挡住 `data/*.zip`、`*.csv`、`Kimore/`、`*.avi`、`*.mp4`，
但放行了 `data/README.md` 与 `data/SHA256SUMS.txt`——说明和清单要进 Git，大文件不进。
