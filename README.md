# Claudio

> 个人 AI 电台 · 读懂听歌习惯 → 规划声音 → 像 DJ 那样播报。
>
> 复刻自 [@mmguo 的 Claudio 施工图](https://www.douyin.com/)。把你 14 年的歌单蒸馏成一个 AI 电台。

```
┌────────────────────────────────────────────────────────────────┐
│ 第四层  PWA · localhost:8080  Player / Profile / Settings      │
│         ↕ HTTP: /now /api/taste /api/chat /api/plan/today      │
│         ↕ WS:   /stream                                         │
├────────────────────────────────────────────────────────────────┤
│ 第三层  Context window · 6 片粘成 prompt                        │
│         ① system  ② user/*  ③ env  ④ memory  ⑤ input  ⑥ trace │
├────────────────────────────────────────────────────────────────┤
│ 第二层  本地大脑                                                │
│         router · context · claude · scheduler · tts · state.db │
├────────────────────────────────────────────────────────────────┤
│ 第一层  USER taste.md · BRAIN claude CLI · MUSIC ncm · I/O fish│
│                                            · feishu · weather  │
│                                            · upnp              │
└────────────────────────────────────────────────────────────────┘
```

## 跑起来

```bash
# 1. 装依赖
npm install

# 2. 配置环境
cp .env.example .env
# 至少填上 FISH_API_KEY，otherwise Claudio 不会开口（音乐还能放）

# 3. 启动
npm start
```

打开 http://localhost:8080。第一次需要你点一下播放按钮以解锁浏览器音频。

## 依赖的外部 API

Claudio 自己不持有任何重模型，全部委托给已有服务：

| 角色 | 来源 | 备注 |
|---|---|---|
| 大脑 | `claude` CLI | Max 订阅即可，无需 API key |
| 音乐 | [NeteaseCloudMusicApi](https://github.com/Binaryify/NeteaseCloudMusicApi) | 本地起一个，默认 :3000 |
| 语音 | [Fish Audio](https://fish.audio) | 需要 API key |
| 日程 | 飞书开放平台 | 可选；不填就不读日历 |
| 天气 | OpenWeather | 可选；不填就当无天气 |
| 客厅 | UPnP/AVTransport | 可选；不填就只在浏览器里放 |

## 项目结构

```
claudio/
├── server/
│   ├── index.js          ← Express + WS 入口
│   ├── router.js         ← 意图分流（skip/pause/search 直连）
│   ├── context.js        ← 6 片提示词组装
│   ├── claude.js         ← spawn `claude -p --output-format json`
│   ├── scheduler.js      ← 07:00 / 09:00 / 22:30 等节律
│   ├── tts.js            ← Fish Audio → cache/tts/<hash>.mp3
│   ├── state.js          ← SQLite (messages / plays / plan / prefs)
│   └── adapters/
│       ├── netease.js
│       ├── fish.js
│       ├── feishu.js
│       ├── weather.js
│       └── upnp.js
├── prompts/
│   └── dj-persona.md     ← Claudio 的 system prompt
├── user/                 ← 这是真正属于你的几个文件
│   ├── taste.md
│   ├── routines.md
│   ├── playlists.json
│   └── mood-rules.md
├── pwa/                  ← Progressive Web App
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   ├── manifest.webmanifest
│   └── sw.js
└── cache/tts/            ← 同一句话只合成一次
```

## HTTP 合约

```
GET  /now                  当前播放状态
GET  /api/taste            读取 user/*.md
POST /api/chat   { text }  发一条消息给 Claudio
GET  /api/plan/today       今天的播放计划（早 7 点生成）
POST /api/feedback         👍/👎/skip 回写到 state.db
WS   /stream               推 now-playing 和 say
```

## 调度

Scheduler 默认在这些时间点触发，每次会重新组装 6 片 context，跑一次大脑：

- 07:00 morning-plan（生成今日 plan，存进 state.db）
- 09:00 commute
- 12:00 lunch
- 14:00 mood-check
- 18:00 evening
- 22:30 wind-down
- 每整点一次 hourly mood-check

## 怎样让它"懂你"

改 `user/taste.md` 和 `user/routines.md`。Claudio 每次组装上下文都会把它们读进去——这是它对你的全部认知。

跑一阵之后，它的 `state.db` 会积累播放/反馈/历史，下一次大脑思考会顾及。

## 没有 Claude CLI 怎么办

`server/claude.js` 在 spawn 失败时会落到一个确定性 stub，按时段返回锚定歌单。这样在没装 CLI 的机器上也能拿到端到端的体验，方便先把音频管线打通再接大脑。
