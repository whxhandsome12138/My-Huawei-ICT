# 数据目录：为什么这里是空的

这个目录**故意不放大文件**。不是忘了传，是三条硬约束：

1. **体积**。KIMORE 作者包 `CG` 1.81 GB、`GPP` 1.67 GB。
   GitHub 单文件硬上限 **100 MB**（超过直接拒收，连 push 都过不去），
   免费 Git LFS 只有 1 GB 存储 / 1 GB 月流量——两个 zip 加起来 3.5 GB，塞不进任何免费额度。
2. **许可**。KIMORE 是 UNIVPM 发布的科研数据集，使用需遵守作者的使用条款；
   把它原样再分发到一个公开仓库，等于替作者重新授权，这一步我们没有权利做。
3. **论文**。`draftKIMORE.pdf` 是 IEEE TNSRE 论文的作者草稿，版权在 IEEE / 作者。
   仓库里做的是**引用**，不是再分发。

所以我们保留的是**可验证的引用**：哈希 + 结构 + 获取方式。任何人拿到同一份数据，
用下面的哈希一对，就知道是不是同一份——这比把 3.5 GB 二进制放进来更可靠，也不越权。

## 需要哪几个文件

| 文件 | 大小 | 作用 | SHA256 |
| :-- | --: | :-- | :-- |
| `CG-*.zip` | 1.81 GB | 健康组作者包（`CG/Expert`、`CG/NotExpert`，含 `.m` 脚本与深度 AVI） | `d5724dca…3653f8` |
| `GPP-*.zip` | 1.67 GB | 患者组作者包（`GPP/BackPain`、`Stroke`、`Parkinson`） | `46b934cb…9f1f00` |
| `archive.zip` | 178 MB | 只有骨架 + 标签的精简包（顶层目录 `Kimore/`，网页/脚本最常用） | `ea1569e9…42b09a` |
| `draftKIMORE.pdf` | 1.9 MB | 论文草稿（口径依据） | `18db6903…509b73e` |

完整哈希见同目录 `SHA256SUMS.txt`（`sha256sum -c` 可直接校验）。

## 数据放哪

`mcp_server` 只需要一个能指到 `Kimore/` 的根目录，两种摆法都行：

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

## 怎么校验

```bash
# 1. 校验下载到的文件（Linux/macOS）
sha256sum -c data/SHA256SUMS.txt

# 2. 跨平台（Windows 也能用）
python tools/check_data.py --root /path/to/reference
```

`check_data.py` 会把「缺失 / 大小不符 / 哈希不符 / 通过」逐条打印，
并提示还差哪几个文件才能跑评估内核。

## 拿到数据的途径

- 官方：KIMORE 论文（Capecci et al., IEEE TNSRE 2019）给出的数据集申请渠道；
- 镜像：Kaggle 上的 KIMORE 副本（作者包 `CG` / `GPP` 的常见来源，许可以其页面为准）；
- 本地：本仓库开发者用的是 `E:\study\3u\ICT\reference\`（不在仓内）。

拿到之后**不要** `git add` 进来：`.gitignore` 已经挡了 `data/*.zip`、`*.pdf`、`Kimore/`。
