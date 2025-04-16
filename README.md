# 介绍

给聊天增加了一个好感度值，靠检测llm模型输出特殊的值来实现，让llm模来判断好感度的上升或下降，并且过低的好感度值会被机器人自动拉黑，有管理员身份来自定义好感度值以及拉黑或移除用户（轻微防止被群U玩坏）
#使用JSON文件存储好感度数据和黑名单数据自动保存在data/FavorSystem目录

# 使用

插件配置可以配置管理员与其他关键数值，但使用前记得先/new和/reset，聊天记得观察对话是否有输出[好感度上升/下降/持平]如果没有请在/new和/reset一遍试试，或者最好的办法人格提示词加一串下面的提示词：

[系统提示]请根据对话质量在回复末尾添加[好感度持平]，[好感度上升]或[好感度下降]标记。示例：用户：你好！你：你好呀！今天过得怎么样？[好感度上升]

指令：

/好感度：查询自己的好感度

/管理 好感度 （管理员）查看所有已经记录的好感度值   

/管理 黑名单 （管理员）查看在黑名单的用户

/管理 白名单 （管理员）查看在白名单的用户 

/管理 修改 <用户ID> <数值>（管理员）修改指定用户的好感度值

/管理 加入黑名单 <用户ID>（管理员）

/管理 移出黑名单 <用户ID>（管理员）

/管理 加入白名单 <用户ID>（管理员）

/管理 移出白名单 <用户ID>（管理员）


## 更新日志

0.3.0：感谢lxfight提出的建议，增加了_conf_schema.json文件，你现在可以在插件配置那里直接修改一些关键配置了，修改并新增加了两命令用于查询黑/白名单的人员

0.2.0：优化了代码，优化了数据持久化，新增加了锁定好感度功能(白名单)，更改了触发（中文这下能记住了吧），新增加了插件直接向llm模型输出关键的提示词（建议还是在人格中增加，貌似人格中的提示词更有权重）

0.13：修复了添加移除黑名单异常的情况

## 🙏 致谢

- AstrBot核心开发团队的技术支持

如果本项目给您带来欢乐，欢迎点亮⭐️，您的支持是我不断前进的动力！

如果您有任何好的意见和想法，或者发现了bug，请随时提ISSUE，非常欢迎您的反馈和建议。我会认真阅读每一条反馈，并努力改进项目，提供更好的用户体验。

感谢您的支持与关注，期待与您共同进步！