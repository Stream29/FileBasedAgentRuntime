## 基本构想
对模型可见的范围内（对模型来说是根目录）只有这样的结构：
```aiignore
/workspace/
/storage/
guideline.md
context_window_main.md
```

模型的system prompt中，全量加载guideline.md和context_window.md，并且加载/workspace/文件夹和/storage/文件夹的目录层次结构。

对模型提供工具，可以对以上的根目录执行任意指令并获取反馈（比如类似claude对workspacegrep一下）

对模型提供工具，可以生成一个sub_agent并调用。sub_agent有和parent_agent同等的能力（除了不能send_message），并且有自己的context_window_sub0.md，它由parent_agent初始化，任务完成后由parent_agent读取。

不允许模型并行调用工具，每次调用工具以后就把信息更新到context_window.md下，不保留任何对话记录。

对模型提供工具，可以读取或修改根目录下的若干行之间的文件（在guideline.md中提示尽量不要全量编辑）

在/storage/文件夹下，以dify plugin为例，存放若干document和few shot。

模型在/workspace/文件夹下工作。

## 为什么可行？
我相信随着模型能力的提升，一定有能力编排更加复杂的工具调用，fygen就是个很好的例子。只要我们有能力帮助它获取到对应的document和few shot，提供合理的工具，它就能完成一个scope下的任务。
同理，我相信随着模型能力的提升，一定有能力编排更复杂的context window，并且合理处理不同agent之间的context window关注点分离。

## 为什么值得尝试？
这个做法可能很粗糙，甚至当前阶段模型的能力不一定能做得好。
但是，作为文件系统：
- 它可以以最简单的方式manage一个有状态的multi agent系统，从memory到document retrieve。
- 这个系统的状态是可fork的。这个系统的初始状态可能没办法胜任编写plugin这样的任务，但是通过适当简单调教就可以完成context的更新，并且调教起来很流畅，符合llm-ops的理念。
- 这个系统的状态是可trace的。基于文件系统则可用git管理，开发迭代效率很高。比如从某个revision的通用coding agent，fork出一个分支，往/storage/里面加一点某个领域特定的文档，再调教一下，就得到了一个某个领域能力强化的分支。