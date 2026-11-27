# 本体与 SHACL 约束校验报告

数据图：`ontology.ttl`（264 三元组）+ `features.ttl`（269 三元组）+ `examples_good.ttl`
约束图：`shapes.ttl`（196 三元组）

## 一、期望

| 检查项 | 结果 |
| :-- | :-- |
| 合规实例通过约束 | 通过 |
| 违规实例被拦下 | 通过 |
| 违规原因不少于 4 条 | 通过 |

## 二、合规实例（期望通过）

**Conforms: True**

```
Validation Report
Conforms: True
```

## 三、违规实例（期望被拦下）

**Conforms: False**，命中 7 条。

```
Validation Report
Conforms: False
Results (7):
Constraint Violation in MinCountConstraintComponent (http://www.w3.org/ns/shacl#MinCountConstraintComponent):
	Severity: sh:Violation
	Source Shape: [ sh:datatype xsd:string ; sh:message Literal("特征必须能追到作者脚本的具体行号，例如 feat_extract_Ex2.m:26。", lang=zh) ; sh:minCount Literal("1", datatype=xsd:integer) ; sh:path kimore:hasSourceLine ; sh:pattern Literal("\.m:[0-9]") ]
	Focus Node: kimore:feature_no_source
	Result Path: kimore:hasSourceLine
	Message: 特征必须能追到作者脚本的具体行号，例如 feat_extract_Ex2.m:26。
Constraint Violation in MinCountConstraintComponent (http://www.w3.org/ns/shacl#MinCountConstraintComponent):
	Severity: sh:Violation
	Source Shape: [ sh:message Literal("方案必须显式声明至少三条不提供的结论（诊断 / 疗效 / 处方 等）。", lang=zh) ; sh:minCount Literal("3", datatype=xsd:integer) ; sh:path kimore:notProvided ]
	Focus Node: kimore:plan_bad
	Result Path: kimore:notProvided
	Message: 方案必须显式声明至少三条不提供的结论（诊断 / 疗效 / 处方 等）。
Constraint Violation in MinCountConstraintComponent (http://www.w3.org/ns/shacl#MinCountConstraintComponent):
	Severity: sh:Violation
	Source Shape: [ sh:message Literal("至少一条证据条目。", lang=zh) ; sh:minCount Literal("1", datatype=xsd:integer) ; sh:path kimore:supportedBy ]
	Focus Node: kimore:dev_bad
	Result Path: kimore:supportedBy
	Message: 至少一条证据条目。
Constraint Violation in SPARQLConstraintComponent (http://www.w3.org/ns/shacl#SPARQLConstraintComponent):
	Severity: sh:Violation
	Source Shape: kimore:AssessmentShape
	Focus Node: kimore:assessment_bad
	Value Node: kimore:assessment_bad
	Source Constraint: [ rdf:type sh:SPARQLConstraint ; sh:message Literal("该样本没有历史临床评分，不得产生任何偏离项——只能报告特征值并建议复测。", lang=zh) ; sh:select Literal("
            SELECT $this ?dev
            WHERE {
                $this kimore:observedLabelPresent false .
                ?dev kimore:derivedFromAssessment $this .
            }
        ") ]
	Message: 该样本没有历史临床评分，不得产生任何偏离项——只能报告特征值并建议复测。
Constraint Violation in SPARQLConstraintComponent (http://www.w3.org/ns/shacl#SPARQLConstraintComponent):
	Severity: sh:Violation
	Source Shape: kimore:DeviationShape
	Focus Node: kimore:dev_bad
	Value Node: kimore:dev_bad
	Source Constraint: [ rdf:type sh:SPARQLConstraint ; sh:message Literal("置信度低于 0.6 的偏离项应标注为『建议复测』，不得直接给出训练调整。", lang=zh) ; sh:select Literal("
            SELECT $this ?c
            WHERE {
                $this kimore:confidence ?c .
                FILTER (?c < 0.6)
            }
        ") ; sh:severity sh:Warning ]
	Message: 置信度低于 0.6 的偏离项应标注为『建议复测』，不得直接给出训练调整。
Constraint Violation in SPARQLConstraintComponent (http://www.w3.org/ns/shacl#SPARQLConstraintComponent):
	Severity: sh:Violation
	Source Shape: kimore:FeatureShape
	Focus Node: kimore:feature_no_source
	Value Node: kimore:feature_no_source
	Source Constraint: [ rdf:type sh:SPARQLConstraint ; sh:message Literal("角度类特征若依赖相机竖直轴，必须绑定符号约定，否则不得进入解释文案。", lang=zh) ; sh:select Literal("
            SELECT $this ?unit
            WHERE {
                $this kimore:unit ?unit .
                $this kimore:verticalReferenceIndependent false .
                FILTER (?unit = "degree")
                FILTER NOT EXISTS { $this kimore:hasSignConvention ?s }
            }
        ") ]
	Message: 角度类特征若依赖相机竖直轴，必须绑定符号约定，否则不得进入解释文案。
Constraint Violation in SPARQLConstraintComponent (http://www.w3.org/ns/shacl#SPARQLConstraintComponent):
	Severity: sh:Violation
	Source Shape: kimore:PlanShape
	Focus Node: kimore:plan_bad
	Value Node: kimore:plan_bad
	Source Constraint: [ rdf:type sh:SPARQLConstraint ; sh:message Literal("方案文本中不得出现诊断、处方、治愈、确诊等医疗结论性措辞。", lang=zh) ; sh:select Literal("
            SELECT $this ?label
            WHERE {
                $this rdfs:label ?label .
                FILTER (
                    CONTAINS(STR(?label), "诊断") ||
                    CONTAINS(STR(?label), "处方") ||
                    CONTAINS(STR(?label), "治愈") ||
                    CONTAINS(STR(?label), "确诊")
                )
            }
        ") ]
	Message: 方案文本中不得出现诊断、处方、治愈、确诊等医疗结论性措辞。
```
