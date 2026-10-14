from __future__ import annotations

DOMESTIC_PLATFORMS: dict[str, dict[str, str]] = {
    "douyin": {
        "label": "抖音",
        "site": "douyin.com",
        "domain_hint": "douyin",
    },
    "kuaishou": {
        "label": "快手",
        "site": "kuaishou.com",
        "domain_hint": "kuaishou",
    },
    "wechat_channels": {
        "label": "微信视频号",
        "site": "channels.weixin.qq.com",
        "domain_hint": "weixin",
    },
    "xiaohongshu": {
        "label": "小红书",
        "site": "xiaohongshu.com",
        "domain_hint": "xiaohongshu",
    },
    "bilibili": {
        "label": "B站",
        "site": "bilibili.com",
        "domain_hint": "bilibili",
    },
}
