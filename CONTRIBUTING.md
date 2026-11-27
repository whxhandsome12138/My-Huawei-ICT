# 参与贡献

这个仓库是「聊愈有方」项目的开源部分，最初为华为 ICT 大赛赛题三准备，会继续维护。
欢迎提 issue、补评测用例、加动作支持。

## 最能帮上忙的三件事

1. **补评测用例**：`eval/eval_set_es2.json` 是 20 条，覆盖八类场景。
   如果你发现某个问法答错了，加一条进去就是最好的贡献——问题 + 判分要点即可。
2. **扩动作**：目前只支持 Es2（躯干侧倾）。Es1/Es3/Es4/Es5 需要各自的判定口径与参照分布，
   骨架在 `ontology/ontology.ttl` 里已经预留（`exercise_Es1`、`exercise_Es3`… 目前 version=0.0）。
3. **改实现**：`tools/verify_features.py` 是 17 个特征的 numpy 参考实现，
   和作者 MATLAB 流程的复算误差 ≤0.02°，但有两处已知差异（见 `docs/FEATURE_PROVENANCE.md` 末尾），
   欢迎把峰检测的等价性彻底对上。

## 动手之前

```bash
git clone <your-fork>
cd mcp_server && pip install -r requirements.txt
python selfcheck.py --port 9100        # 必须 17/17 PASS
python ../tools/validate_ontology.py   # 必须 good=True / bad=7 条命中
```

两条不变量，改代码时别破坏：

- **数字只能来自工具返回值**。不要为了让答案好看而在服务端「补」一个数。
- **不确定就返回 `partial` 或 `error`**，不要编一个 `ok`。模型和人都能处理缺失，处理不了假数据。

## 提交

- 一个 PR 一件事，标题写清楚「修什么 / 加什么」。
- 改了工具返回结构 → 同步改 `mcp_server/fixtures/` 与 `selfcheck.py`，否则 CI 会红。
- 改了特征定义 → 同步改 `docs/FEATURE_PROVENANCE.md` 与 `ontology/features.ttl`，
  两份不一致时 `gen_ontology_features.py --check` 会报错。
- 新增依赖请说明理由；这个项目刻意保持依赖极少。

## 不要做的事

- 不要把 KIMORE 原始数据、视频、任何个人健康信息提交进来。
- 不要把模型 API Key 提交进来（`.env` 已在 `.gitignore` 里）。
- 不要把它描述成医疗器械、诊断工具或疗效评估工具。

## 许可证

提交即表示同意以 [MIT](LICENSE) 授权你的贡献。
