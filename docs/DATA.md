# 数据：从哪来、怎么放、为什么不进 Git 历史

## 一句话

**数据不在 Git 里，但可以从 Release 直接下载**（经数据集作者同意再分发）：

**https://github.com/whxhandsome12138/My-Huawei-ICT/releases/tag/data-v1.0**

不想下载也能跑——仓库自带的 `fixtures/` 足够演示与自检。

**下载后先对一下哈希**（`data/SHA256SUMS.txt`），确认和大家用的是同一份数据：

```bash
sha256sum -c data/SHA256SUMS.txt      # Linux / macOS
python tools/check_data.py --root <放 zip 的目录>   # 跨平台，逐条报通过/缺失/大小不符/哈希不符
```

| 文件 | 体积 | 作用 | SHA256 前 8 位 |
| :-- | --: | :-- | :-- |
| `CG-*.zip` | 1.81 GB | 健康组作者包（`Expert` / `NotExpert`，含 `.m` 脚本与深度 AVI） | `d5724dca` |
| `GPP-*.zip` | 1.67 GB | 患者组作者包（`BackPain` / `Stroke` / `Parkinson`） | `46b934cb` |
| `archive.zip` | 178 MB | 精简包（只有骨架与标签，顶层 `Kimore/`） | `ea1569e9` |
| `draftKIMORE.pdf` | 1.9 MB | 论文草稿（口径依据） | `18db6903` |

**为什么走 Release 而不是 `git add`**：GitHub 单文件硬上限 100 MB，作者包 1.81 GB / 1.67 GB
连 push 都过不去；免费 Git LFS 只有 1 GB 额度，两个包合计 3.5 GB。Release 附件单文件上限 2 GiB，
正好放得下，而且不拖慢 `git clone`——克隆代码几秒钟，要数据的人再单独下。
授权与使用范围见 [`data/README.md`](../data/README.md) 与 [`NOTICE`](../NOTICE)（仅科研与教学，需引用原文）。

---

## 1. 数据是什么

KIMORE 数据集：78 名受试者（专家 17 / 非专家 27 / 腰痛 8 / 卒中 10 / 帕金森 16），
每人做 5 个临床标准动作，共 398 段记录，配套治疗师用 EAAQ 量表给出的临床评分。

每段记录包含：

```
Kimore/<CG|GPP>/<Group>/<SID>/Es<1-5>/
  Raw/JointPosition*.csv      # 25 关节 × (x, y, z, trackingState) = 100 列，无表头
  Raw/JointOrientation*.csv   # 关节朝向
  Raw/TimeStamp*.csv          # 时间戳，单位 100 纳秒（Kinect FILETIME tick）
  Label/ClinicalAssessment_<SID>.xlsx   # cTS / cPO / cCF 三层汇总分
  Label/SuppInfo_<SID>.xlsx             # 组别、年龄、性别
```

**关键约束**：公开的评分只有三层汇总（cTS 10–50、cPO 0–15、cCF 7–35），
**没有 EAAQ 的 10 个分项**。所以本项目的「分项解释」是由特征 + 规则 + 本体推出来的，
不是从标签里学出来的——这一点在文档里必须写清楚，别说过头。

## 2. 引用

```bibtex
@article{capecci2019kimore,
  title   = {The KIMORE dataset: KInematic assessment of MOvements and clinical scores
             for telerehabilitation of low back pain},
  author  = {Capecci, Marianna and Ceravolo, Maria Gabriella and Ferracuti, Francesco and others},
  journal = {IEEE Transactions on Neural Systems and Rehabilitation Engineering},
  volume  = {27}, number = {7}, pages = {1436--1448}, year = {2019}
}
```

## 3. 怎么放

```bash
# 解压后应该是这样（顶层目录名大小写不敏感）
<你的数据根>/
  Kimore/
    CG/Expert/E_ID1/Es2/Raw/JointPosition011214_103845.csv
    CG/NotExpert/NE_ID1/Es1/...
    GPP/BackPain/B_ID1/Es3/...
```

然后二选一：

```bash
# A. 命令行指定
python server.py --port 9100 --data-root "D:/datasets/Kimore"

# B. 环境变量 / compose
# .env 里写 KIMORE_DATA=D:/datasets/Kimore
docker compose -f mcp_server/compose.yml up -d --build
```

> 当前仓库里的 `server.py` 是**回放实现**：它按契约返回 `fixtures/` 里的真实样例，
> 用来在没有数据、没有评估内核的机器上把整条链路跑通。
> 接真实骨架做在线计算，需要实现特征内核——17 个特征的公式、单位、脚本行号都在
> [`FEATURE_PROVENANCE.md`](FEATURE_PROVENANCE.md) 里，`tools/verify_features.py` 是一份
> 可运行的 numpy 参考实现（对作者 MATLAB 流程复算，误差 ≤0.02°）。

## 4. 为什么不进 Git

| 原因 | 说明 |
| :-- | :-- |
| 体量 | 186 MB / 1983 个文件，克隆体验会很差 |
| 条款 | 数据集由论文作者提供，通常限科研用途、要求引用，不允许二次分发 |
| 隐私 | 虽然是去标识化的，但没有必要让它跟着代码到处跑 |

`.gitignore` 已经挡住 `data/`、`Kimore/`、`*.csv`、`*.avi`、`*.xlsx`。
唯一放行的 JSON 是 `mcp_server/fixtures/*.json`——那是工具返回值的结构化摘要，
不含骨架坐标、不含视频、不含个人身份信息。

## 5. 数据质量：接手前必须知道的五件事

1. **时间戳单位是 100 纳秒**，不是秒。680 帧 ÷ 22.67 秒 = 30 fps，作者脚本里的 `sample=30` 是旁证。
2. **评分表里有 19 个组合是不可用的**，不是笼统的「缺 7 个」。判据（`tools/label_audit.py` 可复现）：
   A2 受试者 ID 与目录一致 + 三个分在量表区间内 + `cTS = cPO + cCF`。

   | 项 | 数量 |
   | :-- | --: |
   | 评分表工作簿 | 393 |
   | 受试者 | **78**（与论文一致） |
   | 有效「受试者 × 动作」组合 | **374** |
   | 五项齐全的受试者 | **74** |
   | 至少一项有效的受试者 | **75** |

   19 个无效组合全部明细：`E_ID17` Es1–Es5（五格全空）、`E_ID8` Es1–Es5（同一份空白文件，
   早先只发现了 Es2）、`NE_ID2` Es1–Es5（文件里是 `E_ID1` 的分数，ID 不符）、
   `E_ID3` Es3/Es4/Es5（同样是 `E_ID1` 的分数）、`E_ID16` Es2（文件里是 `E_ID17` 的分数）。
   另有 5 个组合缺骨架文件（`E_ID8`·Es2、`NE_ID24`·Es2、`NE_ID11`·Es5、`B_ID8`·Es4、`S_ID5`·Es3）。
   **`B_ID8` 五个动作都有分，不是缺分样本。**
3. **四个数各说各的用途，不要合成一个**：论文口径 78 人；本地有效标签 374 组合 / 74 人五项齐全；
   参照分布 72 人 / 76 段；带标签建模 67 人 / 67 段（过质量门且有唯一自有标签）。
4. **帧数差异极大**：最短 7 帧、中位 681、最长 2487。少于 100 帧的样本基本没法算运动学指标。
5. **有重复录制**：`NE_ID16` 2 段、`NE_ID27` 4 段。按受试者聚合时统一**取中位**（若取首段，
   4 段录制的受试者在参照分布里权重会翻 4 倍）。服务端响应里的 `quality` 字段标明每段的质量位。
