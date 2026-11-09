/**
 * 首装默认 Pack（N10）
 *
 * 背景：新装扩展 chrome.storage.local["packs"] 为空 ⇒ 零 Pack 空列表。
 * DEFAULT_PACKS 此前只存在于从未接线的 pack-storage-manager.js（PR #13 删除），
 * 内容从 git 历史（5c4eabc^）还原，schema 与现行存储层一致
 * （metadata.pack_id/pack_name/description + workflow.steps）。
 *
 * 写入时机：仅 onInstalled(reason === "install") 且 storage 为空时播种
 * （见 service-worker.js 的 seedDefaultPacksIfEmpty）。
 * update 不播种、已有 Pack 不覆盖——用户删光/自行导入的选择必须被尊重。
 */

export const DEFAULT_PACKS = [
  {
    metadata: {
      pack_id: "knowledge-query",
      pack_name: "知识问答",
      description: "多平台并发查询 → 共识提取 → 灵魂注入",
      version: "2.0",
      type: "productivity",
    },
    workflow: {
      steps: [
        {
          id: "query",
          name: "多平台查询",
          type: "ai",
          prompt_template: "{{prompt}}",
          config: {
            multiPlatform: true,
            soulProfile: "{{soulProfile}}",
          },
        },
      ],
    },
    isDefault: true,
    isUserPack: false,
  },
  {
    metadata: {
      pack_id: "article-writing",
      pack_name: "文章写作",
      description: "收集观点 → 共识整合 → 个性化输出",
      version: "2.0",
      type: "creative",
    },
    workflow: {
      steps: [
        {
          id: "collect",
          name: "观点收集",
          type: "ai",
          prompt_template: "关于{{topic}}的观点和见解",
          config: {
            multiPlatform: true,
            soulProfile: "{{soulProfile}}",
          },
        },
      ],
    },
    isDefault: true,
    isUserPack: false,
  },
];
