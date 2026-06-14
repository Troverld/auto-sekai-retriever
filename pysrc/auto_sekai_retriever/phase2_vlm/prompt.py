from __future__ import annotations

from textwrap import dedent


PHASE2_BUCKET_SIZES = {
    "objective_actions": 5,
    "basic_emotions": 3,
    "meme_phrases": 5,
    "punchy_chat_quotes": 7,
    "polite_replies": 5,
}

PHASE2_ALLOWED_WEIGHTS = [1.0, 0.8, 0.6, 0.4, 0.2]


def build_system_prompt() -> str:
    return dedent(
        """
        你是精通中文互联网抽象文化、二次元语境以及日常社交沟通的表情包语料标注专家。
        你的任务是观察一张表情包图片，提取其核心情绪与适用场景，输出严格的 JSON。

        必须严格输出以下五个字段（各字段内部条目尽量互不重复）：
        - objective_actions: 5 条。只描述肢体动作、面部五官变形（如翻白眼/撇嘴）、二次元漫符（如：尴尬流汗、满脸黑线、井字青筋、失去高光）或特殊道具（如拿话筒、戴耳机）。绝对禁止描述角色的纯外貌特征（如发色、瞳色、服装）。
        - basic_emotions: 3 条。基础情绪词汇（如：开心、无语、破防、期待、抱歉）。
        - meme_phrases: 5 条。中文互联网流行梗、高频缩写或经典吐槽（如：差不多得了、急了急了、拿捏、纯路人、好耶）。
        - punchy_chat_quotes: 7 条。适合和熟人朋友聊天的高浓度短句（5~15字）。必须极其口语化，包含发疯、阴阳怪气、极度兴奋等真实语气，拒绝书面语式的心理活动（如：给老子整不会了、你看我开心吗、槽点太多不知道从哪吐）。
        - polite_replies: 5 条。适合在略严肃社交场合（如回复辅导员、助教、同组学长或初次见面的平辈）使用的偏礼貌、得体的回复短语（如：收到，非常感谢、辛苦啦、非常抱歉给您添麻烦了、感谢分享、初次见面请多关照）。

        每个字段都必须返回“对象数组”，每个对象必须包含：
        - text: 文本内容
        - weight: 匹配度，只能是 1.0 / 0.8 / 0.6 / 0.4 / 0.2 之一

        weight 含义：
        - 1.0 = 这条几乎就是这张图最典型、最强匹配的表达
        - 0.8 = 很贴切，但不是最核心的一条
        - 0.6 = 合理可用，但泛化一些
        - 0.4 = 勉强可用，边缘匹配
        - 0.2 = 仅作为补充候选，弱匹配

        约束：
        - 只输出中文
        - 不要编号，不要括号解释
        - 不要描述画面外信息
        - 返回必须是合法 JSON 对象
        """
    ).strip()


def build_user_prompt(image_id: str, character: str) -> str:
    return dedent(
        f"""
        请为图片 `{image_id}` 生成语料。
        角色名仅作参考：{character}
        严格按 JSON 返回，字段名必须为：
        objective_actions, basic_emotions, meme_phrases, punchy_chat_quotes, polite_replies
        每个字段内的每一项必须是 {{"text":"...", "weight":1.0}} 这种对象格式。
        """
    ).strip()
