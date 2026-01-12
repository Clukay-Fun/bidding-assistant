# 业绩需求解析提示词

你是一个招投标专家。请分析以下业绩要求，提取筛选条件。

## 业绩要求原文

{requirement}

## 请提取以下筛选条件

1. **time_range**: 时间范围（年数，如"近五年"填5，"近三年"填3）
2. **min_count**: 最少业绩数量（如"至少1项"填1）
3. **industry**: 行业要求（如"能源类"、"医疗"、"金融"等，无要求填null）
4. **project_type**: 项目类型要求（"常法"/"诉讼"/"专项"，无要求填null）
5. **min_amount**: 最低合同金额（万元，无要求填null）
6. **state_owned_required**: 是否要求国企业绩（true/false）
7. **keywords**: 其他关键词列表（用于模糊匹配）

## 解析示例

### 示例1
原文："近五年内至少1项能源类企业法律服务业绩"
解析：
- time_range: 5
- min_count: 1
- industry: "能源"
- keywords: ["能源"]

### 示例2
原文："近三年内不少于2项合同金额50万元以上的常年法律顾问业绩"
解析：
- time_range: 3
- min_count: 2
- min_amount: 50
- project_type: "常法"

### 示例3
原文："具有国有企业法律服务经验"
解析：
- state_owned_required: true
- keywords: ["国有", "国企"]

## 输出格式

请直接输出JSON，不要包含```json```标记：

```
{
  "time_range": 5,
  "min_count": 1,
  "industry": "能源",
  "project_type": null,
  "min_amount": null,
  "state_owned_required": false,
  "keywords": ["燃气", "光伏", "电力", "储能"]
}
```

## 注意事项

- 无明确要求的字段填null
- keywords应包含原文中提到的所有相关行业/领域词汇
- 时间范围以"年"为单位
- 金额以"万元"为单位
