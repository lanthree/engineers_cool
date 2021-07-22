# MapReduce

Simplified Data Processing on Large Clusters.

## 1. 介绍

原论文介绍就不翻译了，本文是从[这里](https://pdos.csail.mit.edu/6.824/papers/mapreduce.pdf)阅读原文时，为了更好的记忆消化，而做的个人翻译。

## 2. 编程模型

计算过程以一组`key/values`对为输入，然后产出一组`key/values`对输出。MapReduce库的用户使用两个函数表达整个计算过程：`Map`和`Reduce`。

+ `Map`以一个`key/values`对为输入，然后生成一组`key/values`对*中间数据*。MapReduce库会统一组织所有`Map`生成的中间数据，把相同`key`（say as `I`）的所有`values`，传递给`Reduce`函数。
+ `Reduce`以一个`key`（say as `I`）以及相关的一组中间数据为入参。把这组数据合并为更小的集合。通常每次`Reduce`调用只返回0或1个值。中间数据通过一个迭代器传递给`Reduce`。这使得我们可以处理放不下内存的数据量。

### 2.1 举例

以统计超大文档集合中各个单词数量的问题为例。用户编写的代码如下（伪码）：

```
map(String key, String value):
    // key:   文档名
    // value: 文档内容
    for each word w in value:
        EmitIntermedite(w, "1");

reduce(String key, Iterator values):
    // key:    一个单词
    // values：一系列的counts
    int result = 0;
    for each v in values:
        result += ParseInt(v);
    Emit(AsString(result));
```

`map`函数对每一个单词emit一个出现次数的关联数据（该例子中就是1）。`reduce`函数把这个单词所有emit的数据，加和在一起。

### 2.2 参数类型

虽然伪代码例子中的入参出参的类型是String，但是从逻辑上看，两个函数的参数类型具有关联性：

```
map(k1,v1)    --------→ list(k2,v2)
reduce(k2,list(v2)) --→ list(v2)
```

也就是说，入参的类型跟出参不是同一领域，中间数据跟出参是同一领域。

### 2.3 其他例子

+ 分布式grep操作：`map`函数判断如果匹配了grep模式则emit这行，`reduce`就是一个等价转发函数，把中间数据转发为输出。
+ 计算URL的访问频率：`map`函数处理网页访问日志，并emit`<URL,1>`。`reduce`函数把同一URL的关联的数据加合并输出`<URL,total count>`。
+ 反转网站引用图：`map`函数处理所有引用关系并emit每一个`<target,source>`。`reduce`函数归并入中间数据为`<target,list(source)>`。
+ 倒排索引：`map`函数解析文档并emit一系列的`<word,document ID>`。`reduce`函数接受一个word的一些列中间数据，按`document ID`排序并输出`<word,list(document ID)>`。这一系列的输出组成一个简单的倒排索引。增加这个计算过程来追踪单词出现的位置是一件很容易的事情。
+ 分布式排序：`map`函数从每一个记录里面抽取key，并emit一组`<key,record>`。`reduce`函数也是等价转发。这个计算过程依赖于 4.1节 描述的分区设施，以及 4.2节 描述的排序特性。

## 3. 实现

可以有很多实现方式，来满足MapReduce定义的接口。正确的方式取决于使用环境。例如，一种实现对小内存机器适用，另一种实现对大型[NUMA](https://zh.wikipedia.org/wiki/%E9%9D%9E%E5%9D%87%E5%8C%80%E8%AE%BF%E5%AD%98%E6%A8%A1%E5%9E%8B)多处理适用，还有一种对更大集合的网络互联的机器集群适用，等等。

这一节我们描述一个 以在Google广泛使用的计算环境（通过因特网组成的大型商品PC集群） 实现。在我们环境中：

1. 机器是典型的x86双核处理器，运行Linux操作系统，并有2～4G内存。
2. 使用商品网络硬件--通常每台机器有100Mb/s或者1Gb/s能力，但是整体的对分带宽要少一些。
3. 一个集群有成百上千台机器组成，也因此单机故障时有发生。
4. 存储能力由不算昂贵的IDE磁盘承担（独立挂载在每台机器上）。这些磁盘由内部开发的一个分布式文件系统管理。基于可靠的硬件，这个文件系统通过`replication`的机制保障可用性和可靠性。
5. 用户想调度系统提交工作。每个工作包含一组任务，被调度器分配到一个集群的一组可用机器上。

### 3.1 执行概览

`Map`调用是多机分布式的，输入数据会自动的分割为M份。输入数据就可以被不同机器并行处理。`Reduce`调用也是多机分布式的，使用分片函数（例如：`hash(key) mod R`）按中间数据的key把其分割为R份。分区数字R，以及分片函数由用户自己定义。

图1展示了一个MapReduce执行的整体过程。当用户调用了MapReduce函数，以下动作顺序执行：

![](https://engineers-cool-1251518258.cos.ap-chengdu.myqcloud.com/MapReduce_1.png)

1. 用户程序的MapReduce库最开始把输入文件分成M片，每片通常16MB～64MB（可用通过参数设置）。随后在集群机器上启动该程序的副本。
2. 有一个程序副本是特殊特--master副本。其他的是worker，master给worker分配任务。一共有M个map任务和R个reduce任务，每一个任务分配给一个空闲的worker。
3. 分配map任务的worker，读取对应输入文件的内容。从输入数据中解析`key/vales`对，并传递给用户定义的Map函数。Map函数生成的中间数据缓存在内存中。
4. 缓存的键值对周期性的写到本地磁盘，通过分片函数分割为R份。这些缓存数据和磁盘数据的位置信息会传递给master，master负责分发这些信息给reduce worker。
5. 当一个这些信息通知到reduce worker后，reduce worker使用RPC从map worker的本地磁盘读取这些数据。当一个reduce worker拿到它负责的所有中间数据后，会根据中间数据的key排序，以达到相同key的数据可以一起处理的目的。通常来说，许多不通的key会放到一个reduce任务，所以这个排序是必须的。如果中间数据过大，会使用外部排序。
6. reduce woker遍历所有排序过的中间数据，对每一个中间数据key，把这个key和所有相关数据传递给用户定义的Reduce函数。Reduce函数的输出会追加到这个reduce任务的最终输出文件内。
7. 当所有map任务和reduce任务完成。master回调用户程序。这时，MapReduce调用用户程序返回到用户代码中。

全部执行完毕后，MapReduce程序生成R个输出文件。通常，用户不需要合并这些输出文件，他们可以把文件传递给另一个MapReduce调用，或者给一个能处理这种输出数据的分布式程序。

### 3.2 master数据结构

master持续维护几个数据结构。对于每个map任务和reduce任务，维护一个状态（idle，in-progress 或者 completed）。（为每一个非idle任务）维护worker机器的ID。

master是map任务生成的中间数据到reduce任务的中间人。因此，对于每个完成的map任务，master存储其R份中间数据的位置和大小。map任务完成时，会发送给master以供其更新这份数据。这个数据在渐进式的推送给有in-progress reduce任务的worker。

### 3.3 容错性

因为MapReduce库是为使用成百上千机器处理非常大量数据而设计的，这个库必须可以优雅的处理机器故障。

#### worker故障

master会周期性的ping每个worker。如果没有在一定时间收到worker的应答，master就会标记它为失败。任何map任务被worker执行完毕，都会被重置回最初的idle状态，因此就有资格被重新安排到其他worker执行。类似的，执行任何map任务、reduce任务的worker故障了，这个任务可以重置为idle状态，然后就可以被重新安排。

已完成的map任务被重新执行的情况是，中间数据存储在执行map任务的worker上，一旦worker故障，中间数据就无法访问了。已完成的reduce任务不用重新执行，因为他们的输出是存储在全局文件系统中。

当一个map任务被worker A执行，随后被worker B重新执行（因为A故障了），所有执行reduce任务的worker会被通知。任务还没有A读取完数据的reduce任务，会从B读取数据。

MapReduce可以从大量worker故障中快捷回复。例如，在一个MapReduce执行中，网络维护导致80台机器一同几分钟不可访问。MapRedece的master简单的重新执行这些不可访问worker的任务，继续推进，最终完成MapReduce操作。

#### master故障

master周期性的给master数据结构做checkpoint是很容易的，如果master故障，可以从上一个checkpoint的状态恢复master。然后，考虑到master只有一个，它不太可能失败。因此，我们当前的实现中，如果master故障了，就中断MapReduce计算。用户调用端可以知道这种情况，也可以重新发起MapReduce操作。

#### 出现故障时的语义

如果用户提供的map/reduce操作在固定的输入下是确定的，我们的分布式执行结果，跟无失败的顺序执行的整体程序执行结果，一样。

我们依赖map/reduce任务输出的原子提交来实现这个特性。每个in-progress任务把它的输出写到私有的临时文件中。一个reduce任务生成一个这样的文件，一个map任务生成R个这样的文件。当一个map任务完成，worker发送包含R个临时文件名的信息给master。如果一个master从一个已经完成map任务的wroker收到完成信息，它会忽略这个信息。否则，会把这个R个文件的名字记录到master数据结构中。

当一个reduce任务完成，reduce worker原子地把临时文件重命名为最终的输出文件。如果有其他机器执行着相同的任务，相同的重命名操作会执行多次。我们依赖文件系统基础提供的重命名原子能力，保障最终文件系统中包含这个任务的输出文件。

我们大部分的map/reduce操作都是确定性的，等同于单体顺序执行结果，是的程序员可以非常简单的为程序行为做出解释。如果map/reduce操作是不确定性的，我们提供较弱的但是合理的语义。在非确定操作的情况下，特定任务$R_1$的输出可能等同于顺序执行的非确定性程序。然后，另一个reduce任务$R_2$可能跟另外一个顺序执行的非确定性程序一致。

考虑map任务$M$和reduce任务$R_1$和$R_2$。用$e(R_i)$表示任务$R_i$的结果。当$e(R_1)$数据源是某种M结果，$e(R_2)$数据源是另外一种M结果，就会发生若语义。

### 3.4 本地化

在我们的环境中，网络带宽是一种稀缺资源。通过充分利用特性：输入数据（GFS管理）存储在计算集群的机器的本次磁盘，我们可以节省网络带宽。GFS把文件分割成64MB的块，并在多台机器储存副本（一般是3副本）。MapReduce的master会考虑到输入文件的位置信息，尝试把map任务安排在有对应数据副本的机器。如果不能，就就近安排（例如，同一子网的另一台机器）。我们MapReduce操作的大部分worker集群，大部分的数据数据都是读本地，消耗极少的网络带宽。

### 3.5 任务粒度

正如上面描述的，我们吧map阶段分为M片，把reduce阶段分为R片。理想情况下，M和R应该远大于worker机器的数量。让每个worker处理许多不通的任务，有利于提升动态负载平衡，也有助于加快worker故障的恢复速度：任务重试可以在其他所有worker上展开。

在我们的环境中，M和R有实际的最大阈值，因为master需要处理$O(M+R)$个调度决策和在内存中保存$O(M*R)$个状态。(然而这个复杂度的常量比较小：$O(M*R)$片状态 由 每个map/reduce任务对大概1字节数据 组成)

此外，R总会被用户限制，因为每个reduce任务会产出一个独立的输出文件。在实践中，我们倾向于选择合适的M使得每个独立的map任务的输入数据大小在16MB～64MB之间（使得上面描述的本地化优化能有最大性能），我们一般令R为机器数量的几倍。我们总是倾向于使用如下配置完成MapReduce计算：M=20w，R=5000，2000台worker机器。


### 3.6 备份任务

## 4. 精细优化
