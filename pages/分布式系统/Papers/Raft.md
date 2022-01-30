# Raft

> In Search of an Understandable Consensus Algorithm

## 摘要

> 原论文在[这里](https://pdos.csail.mit.edu/6.824/papers/raft-extended.pdf)

Raft是一种用于管理副本日志的共识算法（Consensus Algorithm）。它提供一个等同于(multi-)Paxos的结果，效率跟Paxos一样，但是组织结构不同于Paxos；这令Raft比Paxos更利于理解，对于建设实际系统提供了更好的基础。为了增加可理解性，Raft分离了共识的关键元素，例如，leader选举、日志副本和安全(safety)，他主张更强的一致性，来减少必须要考虑的状态的数量。一项用户研究的结果表明，对于学生来说，Raft比Paxos更容易学习。Raft还包括一个改变集群中成员关系的新机制，它使用重叠的多数来保证安全。

## 1. 介绍

共识算法允许一批机器像 能够经受其部分成员故障的一致的群体 一样工作。因此，在建设可靠的大型软件系统中，共识算法承担着关键角色。在过去十年中，Paxos算法统治着共识算法的讨论：大部分共识的实现都是基于Paxos或受其影响，Paxos也变成教导学生共识算法的重要工具。

不幸的是，尽管人们极力尝试让它平易近人，Paxos还是非常难懂。此外，为了支持实际系统，它的架构需要复杂的变化。结果，系统的构建者和学生都在与Paxos作斗争。

在亲自跟Paxos斗争之后，我们开始寻找一个新的 能为系统构建和教育提供更好基础 共识算法。我们的方法不同寻常，因为我们的首要目标是可理解性：我们是否可以为实际系统定义一个共识算法，并用一种明显比Paxos容易学习的方式描述它？另外，我们希望算法能够促进直觉的发展，这对于系统构建者来说是必不可少的。重要的不仅是算法是否有效，还在于它能明显地被理解为什么有效。

这项工作的成果是一个称为Raft的共识算法。在设计Raft时，我们应用特殊的技术来提高可理解性，包括分解（Raft分解leader选举、日志副本和安全）和减少状态空间（相对于Paxos，Raft减少了非确定性程度和服务器之间保持一致性的方法）。一项涉及2所大学43名学生的用户研究表明，Raft明显比Paxos容易理解：在学习完两个算法后，其中33名学习对Raft问题的回答比Paxos问题要好。

Raft在许多方面与现有的共识算法相似（最明显的是，Oki和Liskov的Viewstamped Replication），但是特有几个新颖的特性：

+ **强leader**（strong leader）：相对于其他共识算法，Raft使用一种更强形式的leader模式。例如，日志条目（log entries）只能从leader向其他server流动。这减缓了备份日志的管理，也让Raft更容易理解。
+ **leader选举**（leader election）：Raft使用随机的timer来选举leader。这仅仅在任何共识算法都需要的heartbeat上增加一点点机制，但是简单快速地解决了冲突问题。
+ **成员关系变化**（membership changes）：Raft用于更改集群中的服务器集的机制使用了一种新的联合共识（*joint consensus*）方法，在这种方法中，两种不同配置的大部分服务 在转换期间 重叠（overlap）。这允许集群在配置更改期间继续正常运行。

我们相信，无论出于教育目的 还是最为实现基础，Raft都比Paxos更优秀。Raft比其他算法都简单，可理解性更强；描述完整，足以满足实际系统的需要；它有几个开源实现，被多家公司使用；其安全特性已得到正式规定和证明； 其效率可与其他算法相媲美。

论文的其余部分介绍了副本状态机（replicated state machine）问题（第2节），讨论Paxos的优缺点（第 3节），描述我们实现可理解性的一般方法（第4节），介绍Raft共识算法（第5-8节），评估Raft（第9节），并讨论相关工作（第10节）。

## 2. 副本状态机

共识算法通常出现在副本状态机（replicated state machine）的上下文中。在这个方法中，一组server的状态机计算相同状态的相同副本，能在其中一些server故障时继续服务。副本状态机用于在分布式系统中解决许多容错问题。举个例子，拥有单集群master的大型系统 例如 GFS、HDFS、RAMCloud，通常用一个分离的副本状态机来管理leader选举和存储配置信息，达到leader crash还能继续服务的目的。副本状态机的例子包括Chubby、ZooKeeper。

![图1：副本状态机架构。共识算法管理来自client的包含状态机命令的副本日志，让server产生同样的输出。](https://engineers-cool-1251518258.cos.ap-chengdu.myqcloud.com/Raft_P1.png ':size=45%')

如图1所示，副本状态机通常用副本日志实现。每个server存储包含一系列命令的日志，他们的状态机按日志顺序执行。每个日志包含同样顺序的同样命令，所以每个状态机按同样的命令处理同样的命令。因此，这些状态机是确定的，每个计算同样的状态，输出同样的序列。

保持副本日志的一致性就是共识算法的工作。server上的共识模块从多个client接收不同命令，并把命令添加到它的日志中。它与其他server上的共识模块交流，来确保，即使某些server故障，每个日志最终包含相同顺序的同样命令。一旦命令被合适的备份，每个server的状态机按日志顺序处理这些命令，输出被返回给那些client。最终结果，server看上去形成一个单一的、高可用的状态机。

实际系统的共识算法通常具有以下特性：

+ 算法确保在所有非拜占庭（non-Byzantine）条件下的安全性（safety，从不返回不正确的结果）,包括网络延迟、分区（partitions）、丢包、重入和重排序（reordering）等。
    + [拜占庭问题](https://zh.wikipedia.org/wiki/%E6%8B%9C%E5%8D%A0%E5%BA%AD%E5%B0%86%E5%86%9B%E9%97%AE%E9%A2%98)。简单解释是：有间谍（叛徒），跟不同/相同对象返回的决策结果不一致。
+ 只要任意大多数server可执行且能其他server/client通信，算法就是功能完好的（可用的）。因此，通常5台server的集群，可以容忍任意2台server故障。server假设的故障是停止工作；他们也许稍后会从稳定存储中恢复状态并重新加入集群。
+ 算法不能依赖timing来确保日志的一致性：最坏情况下，时钟错误和极端的消息延迟能导致可用性问题。
+ 通常情况下，只要集群的大多数成员响应了一轮RPC，命令就可以完成；少数速度较慢的服务器需要不影响整个系统的性能。

## 3. Paxos的问题是什么？

在过去十年中，Leslit Lamport的Paxos协议几乎已经成为共识的同义词：它是在课堂中最常教授的协议，大多数共识的实现都将其作为起点。Paxos首先定义了一种 能够就单个决定达成一致 的协议，例如单个日志条目备份。我们称这个子集为*single-decree Paxos*。Paxos然后组合该协议的多个实例，以促进一系列决策，如日志(multi-Paxos)。Paxos确保安全性和活性，并且支持集群成员的更改。其正确性已被证明，在通常情况下是有效的。

不幸的是，Paxos有两大弊端。首先，Paxos格外的难以理解。众所周知，完整的解释是模糊的（opaque）；很少有人能够理解它，还需要很大的努力。所以，对于 用简单术语解释Paxos 有很多尝试。这些解释关注于*single-decree Paxos*，但是他们仍然很有挑战性。在一项NSDI 2012参与者的非正式调查中，我们发现，即使是经验丰富的研究人员，也很少有人对Paxos感到舒适。我们亲自跟Paxos作斗争；在 阅读完几个简化解释 和 设计我们自己的替代的协议 前，我们都不能理解完整的协议，而这个过程耗费了一年时间。

我们假设Paxos的不模糊性（opaqueness）来自于它选择single-decree subset作为其基础。Single-decree Paxos是密集而微妙的：它分为没有简单直接解释的两段，而且不能被独立理解。因此，很难产生对于为什么single-decree有效的直观理解。multi-Paxos的组合规则显著增加了复杂度和巧妙性。我们认为，就多项决定达成协商一致意见的总体问题（也就是说，一个日志文件而不是一个单一的条目）可以用其他更直接和明显的方式来分解。

Paxos的第二个问题是，它没有为实际实现提供良好的基础。其中一个原因是，对于multi-Paxos并没有广泛认可的算法。Lamport的描述大多是关于single-decree Paxos；他大致描绘了实现multi-Paxos的可能方法，但是丢失很多细节。已经有几次尝试充实和优化Paxos，但是它们彼此不同，也与Lamport的描绘不同。例如Chubby的系统已经实现了Paxos样子的算法，但在大多数情况下，他们的细节并没有公开。

此外，Paxos结构对于构建实用系统来说是一个糟糕的架构；这是single-decree分解的另一个后果。例如，独立选择日志条目的集合，然后将它们合并到一个顺序日志中几乎没有什么好处；这仅仅增加了复杂性。围绕日志设计一个系统更简单、更有效，其中新条目以受约束的顺序依次附加。另一个问题是，Paxos 在其核心使用对称点对点方法（尽管它最终建议了一种弱领导形式作为性能优化）。在一个只有单个决策问题的简单世界这是有意义的，但是很少有系统使用这种方法。如果必须要做一系列决策，在最开始是选举leader 然后由leader协调决策是 更简单、更快速的。

所以，实际系统与Paxos几乎没有相似之处。每个以Paxos为开始的实现，发现实现它的困难点，然后就会发开一个明显不同的架构。这是费时且容易出错的，而且理解Paxos的困难加剧了问题。Paxos公式（formulation）也许是一个证明它的理论正确性的公式，但实际的实现与Paxos是如此不同，以至于证明几乎没有价值。典型的，下面是来自Chubby实现者的评论：

> Paxos算法的描述 与 真实世界系统的需求 有显著的隔阂......最终的系统会基于一个没有被证明的协议。

因为这些问题，我们认为Paxos没有为系统构建和教育提供很好的基础。在 大型软件系统中共识算法的重要性 背景下，我们决定尝试看我们能否设计一个替代性的 有比Paxos更好特性的 共识算法。Raft就是这个尝试的结果。

## 4. 为了可理解性的设计

设计Raft的目标有多个：它必须为系统构建提供完整的可事件的基础，这样就可以显著减少开发者需要的设计工作；它必须在所有条件下都是安全的，并在典型的操作条件下可用；它必须对普通操作有效。然而我们最重要的目标——也是最大的挑战——是可理解性。它必须能够让大量的用户（audience）轻松地理解算法。此外，它必须有可能开发关于算法的直觉，以便系统构建者可以进行在现实世界实现中不可避免的扩展。

在Raft的设计中，我们需要在许多可选择的方法中进行选择。在这些情况下，我们基于可理解性来评估备选方案：每一种选择解释起来有多难（例如，它的状态空间有多复杂，它有微妙的暗示吗？），以及 对于读者来说，完全理解这种方法及其含义有多容易。

我们认识到在这种分析中存在高度的主观性；尽管如此，我们使用了两种普遍适用的技术。第一种技术是众所周知的问题分解方法：只要有可能，我们就把问题分成可以相对独立地解决、解释和理解的独立部分。例如，在Raft中，我们分离了领导人选举、日志副本、安全以及成员关系变更。

我们的第二个方式是，通过减少考虑的状态的数量来简化状态空间，使系统更加清晰易懂（coherent），尽可能消除不确定性。具体来说，日志不允许有hole，Raft限制了日志相互之间不一致的方式。尽管在大多数情况下，我们试图消除不确定性，在某些情况下，不确定性实际上提高了可理解性。特别地，随机方法引入了不确定性，但它们倾向于通过以类似的方式处理所有可能的选择（选择任意;没关系）。我们用随机化的方法简化了Raft leader的选举算法。

## 5. 共识算法Raft

Raft是用于管理第2节中描述的日志副本的算法。图2以表格的总结了算法，以供参考，图3列举了算法的关键属性；这些图的元素会在接下来的章节展开讨论。

![图2：共识算法Raft的总结（包括成员关系变更和日志压缩）。左上角框中的server行为被描述为一组独立且重复触发的规则。章节号（例如§5.2）表示这一特性将会在哪一节讨论。](https://engineers-cool-1251518258.cos.ap-chengdu.myqcloud.com/Raft_P2.png)

![图3：Raft保证在任何时间每一个属性都是正确的。章节号表示这一属性在哪一节讨论。](https://engineers-cool-1251518258.cos.ap-chengdu.myqcloud.com/Raft_P3.png ':size=45%')

Raft这么实现共识：首先选举出一个leader，然后给这个leader管理日志副本的完整责任。leader从client接收日志条目，备份到其他server，并告诉其他server什么时候可以安全的应用日志条目到它的状态机。有一个leader的设定，简化了日志副本的管理。例如，leader可以在不需要跟其他server交流的情况下独立决策新的日志条目应该放在日志的哪个地方，而且数据也以一种简单的方式从leader流到其他服务器。leader可以故障，可一个与其他server断开连接，在这种情况下，会选举一个新leader。

在leader方法中，Raft分解共识问题为三个相对独立的子问题，这些子问题将会在下面的子章节中讨论：

+ **leader选举**（leader election）：当现leader故障时，必须选举一个新leader（5.2节）。
+ **日志备份**（log replication）：leader必须接收client的日志条目，并把他们备份到全部集群server，促使其他（server的）日志跟他的一样（5.3节）。
+ **安全**（safety）：Raft关键安全属性是图3中的状态机安全属性（State Machine Safety Property）：如果任意server已经对他的状态机应用了特定的日志条目，那么没有其他server会在同样的日志index使用不同的命令（不同的日志条目）。5.4节描述了Raft如何确保这一属性；解决方案包括一个在 5.2节描述的选举机制 的额外约束。

在阐述完共识算法后，这一节讨论可用性的问题，和timing在系统中的作用。

### 5.1 Raft基础

一个Raft集群包含多台server：典型地是5台，这样系统能容忍任意两台故障。在任意给定的时间，每个server都处理下面三个状态中的一个：leader、follower、candidate。在正常的操作中，只会有一个leader，其他server都是follower。follower都是被动的：他们不自己执行请求，只会简单的响应leader和candidate的请求。leader处理所有client的请求（如果client联系到follower，follower会重定向请求到leader）。第三个状态，candidate（在5.2节描述），用于选举一个新的leader。图4展示了状态和他们的转换；下面会讨论这些转换。

![图4：server状态。follower只响应其他server的请求。如果一个follower收不到任何请求，他就会变成candidate，开始选举。candidate如果接收到集群大多数server的投票，他就会成为新的leader。leader通常会一直运作到其故障。](https://engineers-cool-1251518258.cos.ap-chengdu.myqcloud.com/Raft_P4.png ':size=45%')

![图5：时间被划分为term，每个term以选举开始。选举成功后，单leader管理集群，直到term结束。一些选举失败，在这些情况下term会以无leader结束。在不同的服务器上，可以在不同的时间观察term之间的转换。](https://engineers-cool-1251518258.cos.ap-chengdu.myqcloud.com/Raft_P5.png ':size=45%')

如图5所示，Raft把时间划分为任意长度的term。term以连续的整型数字编号。每个term以选举开始，这时一个或多个candidate尝试成为leader（5.2节描述）。如果一个candidate赢得选举，它就会在term剩下的时间以leader的形式服务。在某些情况下，一次选举会造成投票分裂。在这种term中，会没有leader；很会会开始新term，开始新的选举。Raft确保在一个给定的term中最多只有一个leader。

不同的server会在不同的时间观察到term之间的转变，在某些情况下，一个server也许不会观察到一次选举，甚至整个term周期。term就像一个Raft的逻辑时钟，让server能检测过时的信息，如陈旧的leader（stale leader）。每个server存储一个当前term编号，这个编号会随时间单调递增。当前term在server通信时交换；如果一个server的当前term小于其他server，那么他会更新它的当前term为更大的值。如果一个candidate或者leader发现它的term过期了，它会立即退回为follow状态。如果一个server收到了一个过期term编号的请求，它会拒绝这个请求。

Raft的server交流使用RPC，基础的共识算法只需要两种类型的RPC。RequestVote RPC，由candidate在选举期间发出（5.2节），AppendEntries RPC由leader在备份日志条目和提供心跳时发出（5.3节）。第7节为了在server间传送快照引入了第三种RPC。如果server没有一定的时间内接收到响应，就会重试RPC，另外server会并行使用RPC来最优化性能。

### 5.2 leader选举

Raft使用心跳机制来触发leader选举。当server启动时，先成为follower。只要server能从leader或者candidate接收到有效RPC，他就保持为follower状态。leader为了保持其权利会周期性发送心跳（不携带日志条目的AppendEntries RPC）给所有foloower。如果一个follower在election timeout时间内都没有收到任何请求，他就会假设没有活着的leader，然后开始一轮选举来选择一个新的leader。

要开始一轮选举，一个follower增加它当前的term编号，状态变更为candidate。然后他会给他自己头片 以及 并行的给集群中每个其他server发送RequestVote RPC。在以下三种事情任一发生之前，candifate都会保持它的状态：（a）它赢得选举，（b）另外一个server成为leader，（c）一段时间过去了，没有赢家。这些结果会在接下来的段落单独讨论。

如果candidate接收到整个集群大多数server在同一个term内的投票后，它就赢得选举。在一个给定的term，每个server最多时会给一个candidate投票（注意：5.4节对于投票引入了另外一个约束）。“大多数”的规则确保，在一个特定的term中最多时有一个candidate能赢得选举（即图3中的Election Safety Property）。一旦一个candidate赢得选举，就会成为leader。随后它发送心跳信息给其他所有server 来建立它的职权 以及阻止新的选举。

在等待投票时，candidate也许会接收到另一个server发来的 “我是leader” 的AppendEntries RPC。如果leader的term（在RPC内）至少跟candidate的当前term一样大，那么candidate认为这个leader是合法的，然后变为follower状态。如果RPC中的term小于candidate的当前term，那么candidate拒绝RPC，保持candidate状态。

第三种可能的结果，candidate没有赢也没有输：如果多个follower一起成为candidate，投票可能会分散，导致没有candidate能获得大多数的投票。当这个情况发生时，每个candidate会超时，然后增加它的term编号并重新发起一轮选举。然而，如果没有额外的措施，投票分裂的问题可能会无限发生。

Raft使用随机化election timeout来确保投票分裂的问题很少发生，并能被快速解决。为了方式预防投票分裂的发生，election timeout在固定时间间隔中随机选择的（例如，150～300ms）。这在所有server一样，所以大多情况下，只有一个server会超时；它会赢得选举 然后 在任何其他server超时前发送心跳。同样的机制也用来处理投票分裂。每个candidate在选举开始时始随机化election timeout，在启动下一轮投选举前，它就等待时间的流逝；这减少了新一轮选举发生头片分裂的可能性。9.3节展示中，这个方法能很快的选出一个leader。

选举就是一个例子，说明可理解性如何引导我们在设计选择中做出选择。最开始我们计划使用一个排名系统（ranking system）：每个candidate分配一个唯一的排名，用来在竞争的候选人之间进行选择。如果一个candidate没有另一个candidate排名高，那他就退回到follower状态，这样，更高排名的candidate就会更容易赢得下一轮选举。我们发现，这个方法会对可用性产生微妙的问题（如果排名较高的server出现故障，排名较低的server可能需要超时并再次成为candidate，但如果它过早这么做，它会将进程重置为leader选举）。我们在算法上做了几次调整，但是调整后会有新的corner case出现。最终，我们总结的出随机重试方法更显而易见、更易懂。

### 5.3 日志副本

一旦选出一个leader，就开始处理client请求。每个client请求包含一个要被副本状态机执行的命令。leader把命令作为一个新条目追加到它的日志中，然后并行地发送AppendEntries RPC给每一个其他server来备份日志条目。当日志条目被安全的备份（如下描述），leader应用该条目到它的状态机，然后给client返回执行结果。如果follower故障或者缓慢运行，或者网络丢包，leader无限重试AppendEntries RPC（即使在应答client之后）直到所有follower最终保存所有日志条目。

![图6：日志是条目的集合，条目顺序标号。每个条目包含其创建是的term（每个盒子中的数字），以及状态机的命令。如果条目应用给状态机是安全的，那么这个条目就被认为是committed。](https://engineers-cool-1251518258.cos.ap-chengdu.myqcloud.com/Raft_P7.png ':size=45%')

日志像图6中展示一样组织。每个日志条目存储一个状态机命令 以及 当leader接收到这个条目时的term编号。日志条目中的term编号用于检测日志间的不一致，确保图3中的一些属性。每个日志条目还有一个整数index标识它在日志中的位置。

leader决策什么时候应用日志条目到状态机时安全的；这种条目被称为committed。Raft保证committed条目是持久的，会最终被所有可用的状态机执行。一旦leader创建的条目在大多数server中备份，这个条目就是committed（例如，图6的条目7）。这也commit leader日志中先前创建的条目，包括先前leader创建的条目。5.4节讨论在leader变更后应用该规则的一些微妙之处，也表明了committed的定义是安全的。leader持续跟踪他知道的最高index的条目committed，它在以后的AppendEntries RPC（包括心跳）中包含该索引，以便其他服务器最终发现。一旦follower知道一个日志条目是committed的了，它会将其应用到本地状态机（以日志的顺序）。

我们设计Raft日志机制，来保持不同server日志的高级别一致性。这不仅简化了系统行为，也令它更可预测，但是还是确保安全的重要组件。Raft维护以下属性，它们共同构成图3中的Log Matching Preperty：

+ 如果不同日志中的两个条目拥有相同的index和term，他们存储相同的命令。
+ 如果不同日志中的两个条目拥有相同的index和term，那么日志中所有先前的条目都是相同的。

第一个属性遵循这个事实：在一个给定term中的给定的index，leader最多创建一个日志条目，以及 日志条目从不变更它在日志中的位置。第二个属性由一个AppendEntries RPC做的简单一致性检查保证。当发送一个AppendEntries RPC，leader会发 送新条的目前一条目 在日志中的index和term。如果follower没有在日志中发现一样index和term的条目，那它将拒绝新条目。一致性检查作为一个归纳步骤：最初日志空的状态，满足Log Matching Property，一致性检查在日志扩展时保持Log Matching Property。最终，每当AppendEntries返回成功，leader就知道follower的日志跟它自己的日志 一直到（AppendEntries的）新条目 都是相同的。

在正常的操作中，leader和follower的日志保持一致，所以AppendEntries一致性检查从来不会失败。然而，leader故障（crash）可以让日志不一致（老leader可能没能把它所有日志完成备份）。这些不一致会在一系列leader和follower的crash中加剧。图7说明了follower日志可能跟新leader日志不同的方式。follower可能丢失leader存在的条目，也可能会拥有leader没有的条目，或者两者同存。日志条目的中缺少和多余 可能会跨越多个term。

![图7：当最上方的leader当选，情况a～f都有可能在follower日志中发生。每个盒子表示一个日志条目；盒子中的数字是term。follower也许会丢失条目（a～b），也许会有额外的未committed的条目（c～b），或者都发生（e～f）。例如，情况f可能发生 server曾经是term2时期的leader，在它日志中增加几个条目，然后在commit任何一个之前crash；然后很快重启，成为term3的leader，增加了几个条目，然后在commit任何一个之前又一次crash，然后在接下里几个term持续故障。](https://engineers-cool-1251518258.cos.ap-chengdu.myqcloud.com/Raft_P7.png ':size=45%')

在Raft中，leader通过强制让follower的日志跟他自己的一致来解决不一致的问题。这意味着，folloer日志中冲突的条目会被leader日志中的条目覆盖写。5.4节会说明，再加一个限制的情况下，这是安全的。

为了让follower的日志跟它自己的一致，leader必须找到双方日志最新的一致的条目，删除follower日志其后的条目，然后发送leader的所有这之后的条目。这所有的操作在 AppendEntries RPC执行的一致性检查 的响应中发生。leader给每个follower维护nextIndex，表示leader会发送给follower的下一个日志条目的index。当leader刚当选时，它初始化所有的nexIndex值为它日志最后一个条目的下一个index（图7中就是11）。如果follower的日志跟leader的不一致，下一次的AppendEntries RPC的一致性检查会失败。在一次拒绝之后，leader递减nextIndex然后重试Append Entries RPC。最终，nextIndex会到达leader和follower一致的点。这时，AppendEntries就会成功，删除follower日志中任何冲突的条目，添加来自leader日志的条目（如果有）。一旦AppendEntries成功，follower的日志跟leader的一致，在这个term剩下的时间里，它将保持这种状态。

如果需要，可以优化协议，以减少拒绝的AppendEntries RPC的数量。例如，当拒绝一个AppendEntries请求，follower可以包含冲突条目的term和它保存的该term的第一个index。使用这个信息，leader可以递减nextIndex以绕过该项中所有冲突的项。每个包含冲突条目的term需要一次AppendEntries，而不是每个（冲突）条目需要一个RPC。在实践中，我们对这种优化是否真的需要抱有怀疑，因为故障不常发生，有许多不一致条目的情况不太可能出现。

使用这种机制，leader当选时，不需要采取任何特殊的操作来恢复日志一致性。它仅仅从正常操作开始，在AppendEtries一致性检查的失败中，日志自动会收敛。leader从不会覆盖写 或者 删除它自己日志的条目（图3中的Leader Append-Only Preperty）。

此日志复制机制显示了第2节中描述的理想的一致属性：只要大多数机器可用，Raft可以接受、备份、应用新日志条目；在正常的情况中，一轮RPC就可以备份新条目给集群的大多数；单个缓慢的follower不会影响性能。

### 5.4 安全性

前面的章节描述Raft如果选举leader和备份日志条目。然而，目前为止描述的机制并不能十分有效的确保 每个状态机按同样的顺序执行相同的命令。例如，一个follower在leader commit几个日志条目期间不可用，然后它竞选为leader 重写条目；那么，不同的状态机会执行不行的命令序列。

这一节通过在哪些server可以竞选leader增加约束来完善Raft算法。这一约束确保在任一给定的term，leader包含全部先前term中committed的条目（图3的Leader Completeness Property）。在选举约束下，我们给commit行为执行更具体的规则。最终，我们给出了Leader Completeness Property的证明示意图，并展示它怎样引导复制状态机的正确行为。

#### 5.4.1 选举约束

在任何基于leader的共识算法中，leader必须最终存储所有的committed日志条目。在一些共识算法中，例如Viewstamped Replication，即使server起初没有包含所有committed条目，它也可以被选举为leader。这些算法包含了 识别丢失条目、传输给新leader 的额外机制，要么在选举过程中，要么在选举后的短时间内。不幸的是，这导致了相当多的附加机制和复杂性。Raft使用一个简单的方法，保证所有先前term的committed条目 在新leader当举的时候 都在其日志上，而且无需传输条目给leader。这意味着。日志条目仅单向 从leader到follower 流动，leader从不覆盖写它日志中已经存在的条目。

Raft使用投票过程来防止candidate 在它的日志包含所有committed条目 前赢得选举。一个candidate为了选举必须要与集群的大部分server通信，这意味着，每个committed条目必须在至少其中一个server中存在。如果candidate日志至少跟大多数的日志一样新（up-to-date，在下面精确定义），那么会有全部的committed条目。RequestVote RPC实现这一约束：RPC包含关于candidate日志的信息，如果投票者自己的日志比candidate更up-to-date，那么就会拒绝这个candidate的投票。

Raft通过比较日志中最后的条目的index和term来判断哪个日志更up-to-date。如果日志最后条目的term不同，那么更新term的日志更up-to-date。如果日志的term相同，日志更长的更up-to-date。

#### 5.4.2 从先前的term commit条目

如5.3节描述的，一旦它当前term的条目存储在大部分server上后，leader知道该条目是committed。如果leader在commiting条目前crash，未来的leader会尝试结束备份条目。然而，leader不能立即得出 一旦早先term的条目存储在大多数server 该条目就已经committed  的结论。图8阐述了一种情况，老条目存储在大多数server，但仍然可以被一个未来的leader覆盖。

![图8：一个展示为什么leader不能使用老term的日志条目确认commit情况的时间序列。（a）中S1是leader，以index为2备份日志条目到了部分server。（b）中S1 crash；S5由于S3、S4的投票当选term3的leader，在index 2接受了另外一个条目。（c）中S5 crash；S1重启，被选为leader，继续原来的备份。这时，term2的条目已经被备份到大多数server，但没有committed。如果S1在（d）中crash，S5可能被选举为leader（S2、S3、S4投票）然后用它自己term3的条目重写条目。然而，如果在S1 crash前，已经把它当前term的条目备份到大多数server，像（e）中一样，这个条目会被committed（S5不能赢得选举）。这时，所有先前的日志条目也会被committed。](https://engineers-cool-1251518258.cos.ap-chengdu.myqcloud.com/Raft_P8.png ':size=45%')

为了消除图8中的问题，Raft从不通过副本计数来commit先前term的日志条目。只有leader当前term的日志条目通过副本计数来commit：一旦当前term的条目通过这种方式committed，那么所有前面的条目也 因为Log Matching Property 间接的被committed。有些场景下leader可以安全的得出结论：老日志条目是committed（例如，如果这个条目存储在每个server），但是Raft为了简单性选择了一个更保守的方法。

Raft在commit规则中承受这一额外的复杂性，因为当leader从以前的term复制条目时，日志条目会保留它们原来的term编号。在其他共识算法中，如果新leader从先前的“term”备份条目，它必须使用新的“term编号”。Raft的方法可以更好的解释日志条目，因为他们一直在日志中维护同样的term编号。另外，相对于其他算法，Raft中的新leader从前term发送的日志条目更少（其他算法必须发送冗余的日志条目来在commit它们前给它们重新编号）。

#### 5.4.3 安全性讨论

给出完整的Raft算法后，我们现在可以更精确地讨论Leader Completeness Property是否成立（这些讨论基于安全性证明；详见9.2节）。我们假设Leader Completeness Property不成立，然后我们证明矛盾。假设term T的leader（$leader_T$）在它的term commit一个日志条目，但是这个日志条目并没有被未来某个term的leader存储。令leader最小的term $U > T$（$leader_U$）没有存储这个条目。

![图9：如果S1（$leader_T$）在它的term commit一个新条目，S5在随后的term U当选为leader，那么，必定至少有一个server（S3）接受了日志条目也投票给S5。](https://engineers-cool-1251518258.cos.ap-chengdu.myqcloud.com/Raft_P9.png ':size=45%')

1. 这个committed条目肯定在$leader_U$当选时不在它的日志中（leader从不删除/覆盖写它的条目）。
2. $leader_T$在集群的大部分备份了这个条目，$leader_U$从集群大部分获得了投票。因此，至少一个server（投票者）既从$leader_T$接收到了条目，也投票给了$leader_U$，如图9所示。这个投票者就是矛盾的关键。
3. 这个投票者一定在投票给$leader_U$**之前**从$leader_T$接收到committed条目；否则，它会拒绝$leader_T$的AppendEntries请求（它当前term编号会比T高）。
4. 这个投票者在投票给$leader_U$时还存着这个条目，因为（它假设）每个参与的leader包含这个条目，leader从不删除条目，follower只有当条目与leader冲突时才有删除。
5. 这个投票者赞同给$leader_U$的投票，所以$leader_U$的日志必须已经至少跟投票者的一样新。这引出两个矛盾之一。
6. 首先，如果投票者和$leader_U$有同样的最后的日志term，那么$leader_U$的日志必定至少跟投票者的一样新，所以它的日志包含每一个投票者的日志。这就是一个矛盾，因为投票者包含这个committed条目 然而 $leader_U$假设不包含。
7. 否则，$leader_U$的最后的日志term必须大于投票者。而且，比T大，因为投票者最后的term编号至少是T（它包含term T的committed条目）。创建$leader_U$最后的日志条目的前leader必定在他的日志中包含这个committed条目。那么，根据Log Matching Property，$leader_U$的日志一定也包含这个committed条目，这也是个矛盾。
8. 这样就完成了反证。因此，所有term大于T的leader必定包含term T的所有committed的条目。
9. Log Matching Property间接的保证未来的leader也会包含committed的条目，例如图8（d）的index 2。

给定Leader Completeness Property，我们可以证明图3中的State Machine Safety Property，它表明如果一个server已经应用了一个给定index的日志条目到它的状态机，不会有其他server在同样的index应用不同的日志条目。在一个server应用条目到它的状态机时，直到这个条目为止的日志一定与leader相同，而且条目一定是committed。现在考虑任意server应用给定日志index的最小term；Log Completeness Property保证所有更高term的leader会保存同样的日志条目，所以在后面term应用该条目的server会应用同样的值。因此，State Machine Safety Property成立。

最后，Raft要求server按日志顺序应用条目。结合State Matching Safety Property，这意味着所有server会按同样的顺序应用完全一致的日志条目集合到他们的状态机。

### 5.5 follower/candidate crash

在此之前，我们关注于leader故障。follower和candidate的crash相对于leader的crash更容易处理，而且他们用同样的方式处理。如果一个follower或者candidate crash，那么未来的发送给它的RequestVote和AppendEntries RPC会失败。Raft通过无限重试来处理这些失败；如果crash的server重启，然后RPC就会成功完成。如果一个server在处理完RPC 但是在响应前crash，那么它会在重启后接收到一样的RPC。Raft RPC是幂等的，所以这不会造成影响。例如，如果一个follower接收一个 包括已经在它日志内的日志条目的 AppendEntries请求，它会忽略新请求中的这些日志条目。

### 5.6 timing和可用性

我们Raft的一个要求是安全性必须不能依赖于timing：不能仅仅因为某些事件比预期更快或更慢发生，系统就会产生错误的结果。然而，可用性（在一定时间内系统给client响应的能力）不可避免的依赖于timing。例如，在server crash时信息交流话费比一般情况更多的时间，candidate可能不会等待足够的时间赢得选举；没有一个稳定的leader，Raft不能处理其他事情。

leader选举是timming最重要的Raft层面。只要系统满足如下*timing requirement*，Raft就能选举并维护一个稳定的leader：

$$
broadcastTime << electionTimeout << MTBF
$$

在不等式中，broadcastTime是server并行给集群每个server发送RPC并收到回应的平均时间；electionTimeout是5.2节描述的选举超时时间；MTBF单个server的多次故障间隔的平均时间。广播时间应该比选举超时时间小一个数量级，这样leader可以依赖发送心跳信息让follower免于进入选举；给定用于选举超时时间的随机方法，这个不等式也不太可能产生投票分割。选举超时应该比MTBF小几个数量级，这样系统才能稳定运行。当leaer crash，系统会大约有 选举超时 时间的不可用；我们希望这只是整体时间的一小部分。

广播时间和MTBF是底层系统的特性，而选举超时是我们必须选择的。Raft的RPC通常要求接收者持久化存储信息到稳定存储，所以广播时间也许从0.5ms到20md之前，依赖于存储技术。所以，选举超时时间大概介于10ms～500ms之间。通常来说，server的MTBF是几个月或者更多，这很容易满足timing requirement。

## 6. 集群成员关系变更

到此为止，我们假设集群配置（参与共识算法的机器集合）是固定的。实际上，有时候会需要变更变更配置，例如 当机器故障时替换机器、变更副本数量（即机器数机器数）。虽然，我们可以通过让集群整体下线、更新配置文件、然后重启集群 来完成配置变更，但是这会导致在转变过程中不可用。另外，如果有任何人工操作，那就会有操作错误的风险。为了避免这些问题，我们决定使配置变更自动化，并整合到Raft共识算法里面。

为了让配置变更机制安全，就不能在变更过程中有 同一个term两个leader 的情况发生。不幸的是，任何从老配置切换成新配置的方法都不安全。不可能原子的一次性切换所有server的配置，所以集群可能会在变更过程中分裂为两个独立的majority（如图10）。

![图10：直接从一个配置切换为另一个配置是不安全的，因为不同server可能在不同时间切换配置。在这个例子中，集群由3 server增加为5 server。不幸的是，会有某一时间 同一个term可能选举出两个不同的leader，一个是老配置（$C_old$）的majority的结果，另一个是新配置（$C_new$）的majority的结果](https://engineers-cool-1251518258.cos.ap-chengdu.myqcloud.com/Raft_P10.png ':size=45%')

为了确保安全，配置变更必须使用两阶段的方法。有许多不同的两阶段的实现。例如，一些系统使用第一阶段取消老配置，这样进群不能处理client请求；然后第二阶段，使新配置生效。在Raft中，集群首先切换为我们称之为 联合共识（joint consensus）的过度配置；一旦联合共识committed，系统随后变更为新配置。联合共识包含了老配置和新配置：

+ 日志条目备份到两个配置中的所有server。
+ 任意配置的server都可以是leader。
+ 选举和条目commit的，需要老配置和新配置两个配置的majority同意。

联合共识允许单个服务器在不同的时间在不同的配置之间转换，而不影响安全性。此外，联合共识允许集群在整个配置更改过程中继续服务client请求。

![图11：配置变更时间线。虚线表示配置条目创建但没有committed，实线表示最新的配置条目committed。leader首先在它的日志中创建$C_old,new$日志条目，然后向$C_old,new$ commit（$C_old$的大多数 和 $C_new$的大多数。然后，它创建$C_new$日志项，并向$C_new$的大多数commit）。](https://engineers-cool-1251518258.cos.ap-chengdu.myqcloud.com/Raft_P11.png ':size=45%')

集群配置使用备份日志的特殊条目存储和交流；图11阐述了配置变更过程。当leader接收到配置从$C_old$变更为$C_new$的请求，它会存储联合共识配置（图中的$C_old,new$）为日志条目，并用之前描述的机制备份它。一旦一个server把新配置加到它的日志中，它就会用这份配置进行所有未来的决策（server总是使用它日志中最新的配置，不管这个条目是否已经committed）。这意味着，当$C_old,new$的日志条目committed后，leader会使用$C_old,new$的规则进行决策。如果leader crash，一个属于$C_old$或者$C_old,new$的server会被选举为leader，取决于获胜的candidate是否接收到了$C_old,new$。在任何情况下，$C_new$不能在此期间单方面做决策。

一旦$C_old,new$ committed，$C_old$、$C_new$都不能在没有对方的同意下决策，Leader Completeness Property确保只有有$C_old,new$日志条目的server会被选为leader。现在，leader创建描述$C_new$配置的日志条目 并把它备份到集群 就是安全的了。再次强调，server一旦看到这个配置就会立即生效。当新配置在$C_new$的规则下committed，老配置就无关紧要了，不包含在新配置的server也可以shut down了。如图11中展示，$C_old$、$C_new$都不能单方面做决策；这保证了安全性。

对于重新配置，还有三个问题需要解决。第一个问题是，新server也许最初没有存储任何日志条目。如果他们以这个状态加入集群，他们重备份条目需要话相当一段时间，这短时间内，他们也不能commit新日志条目。为了避免可用性问题，Raft在配置变更之前因为了一个额外阶段，此时server以non-voting成员加入集群（leader备份日志条目给他们，但是他们不在majority的考虑范围）。一旦新server补全了集群其他server的日志，配置变更就可以按上面描述的进行。

第二个问题是，集群leader也许可能不是新配置的中的机器。在这种情况，一旦$C_new$日志条目committed，leader就会下台（转变回follower状态）。这意味着，在某一段时间（commit $C_new$日志条目的过程中），leader管理者不包含他自己的集群；它备份日志项，但不把他自己计算在majority范围内。leader变更发生在$C_new$ committed，因为这是新配置可以独立执行的第一时间（从$C_new$中选举一个leader总是可以的）。在此之前，可能会有只有$C_old$的server可以被选举为leader的情况。

第三个问题是，移除的server（那些不在$C_new$中的）可能扰乱集群。这些server不在接收心跳信息，所以，他们会timeout，并发起新的选举。他们会使用新的term发送RequestVote RPC，这回导致当前leader退回follower状态。最终会选出一个新leader，但是移除的server会再次timeout，重复这个过程，导致低可用性。

为了防止这个问题，当server相信当前leader存在时，它会忽略RequestVote RPC。具体的，如果一个server在接收到leader消息后的最小election timeout时间内接收到RequestVote RPC，他就不会更新term，也不会投票。这并不会影响正常的选举，server都在会开始选举前等待至少最小election timeout的时间。然后，这避免了移除的server的扰乱；如果leader能在集群发送心跳，那它就不会被更大的term数字废黜。

## 7. 日志压缩

Raft日志在正常操作期间 为了包含更多client请求 会持续增长，但在实际系统中，它不能无限制增长。随着日志增长，它会占用更多空间，花费更多时间重放。如果没有一个机制可以在无限增长的日志中忽略淘汰的信息，这最终会导致可用性问题。

快照（Snapshotting）是最简单的压缩方法。在快照中，当前整个系统的状态会写入稳定存储介质中的snapshot，之后这个点之前的所有日志都可以忽略掉。快照在Chubby和ZooKeeper中有使用，本节下面的内容会描述Raft的快照。

渐进式的压缩方法，例如，log cleaning、LSM-Tree，也是可以的。这些操作可以同时对部分数据进行操作，所以他们更均匀地分散压实负荷在一段时间内。他们首先选择积累了许多删除和覆盖写的数据区域，然后他们更紧凑的重写这些对象，然后释放这块区域。对比与快捷，这需要额外的机制和复杂性，快照因总是操作整个数据集 简化了问题。相对于log cleaning会要求Raft修改，状态机可以使用跟快照同样的接口实现LSM-Tree。

![图12：一个server使用新的快照替代它日志中的条目（从1到5），快照存储当前状态（例如变量x和y）。快照最后包含的索引和term用于明确快照位于日志条目6之前。](https://engineers-cool-1251518258.cos.ap-chengdu.myqcloud.com/Raft_P12.png ':size=45%')

图12展示了快照的基本思想。每个server独立的进行快照，涵盖它自己日志中的committed条目。大多数工作 包括 状态机将其当前状态写入快照。Raft也会将一小部分元数据写入快照：last included index - 快照替代的日志条目的最后的索引（状态机最后应用的条目索引），last included term - 这个条目的term。保留这些记录是为了支持对快照之后的第一个日志条目进行AppendEntries一致性检查，因为那个条目需要之前的日志索引和term。为了支持集群成员变更（第6节），快照还在最近包含的索引的日志中包含最新的配置。一旦server写完快照，他也许会删除直到last included index的全部日志条目，以及任何之前的快照。

即使server正常独立地进行快照，leader必须偶然的给落后的follower发送快照。这发生在，需要发送给follower的下一个日志条目已经被leader抛弃。幸运的事，这一情况在正常操作中不太会发生：跟随leader节奏的follower都会有这个日志条目。然而，一个异常慢的follower或者一个新加入集群（第6节）可能没有。令这种followerup-to-date的方法是leader通过网络发送快照。

![图13：InstallSnapShot RPC总结。为了传输快照分块；快照传输令follower直到leader存活，所以它会重置election timer。](https://engineers-cool-1251518258.cos.ap-chengdu.myqcloud.com/Raft_P13.png ':size=45%')

leader使用一个称为InstallSnapshot的新RPC给太落后的follower发送快照；如图13。当follower经这个RPC接收一个快照，它必须基于它已有的日志条目决策要做什么。通常，快照会包含还不在接收者日志中的新信息。这种情况下，follower完整丢弃它的日志；全部被快照取代，可能有uncommitted条目与快照冲突。如果follower接收到一个描述它日志前部分的快照（由于重穿或者错误），那么快照覆盖部分的日志条目删除，但是快照之后的条目仍然有效，必须保留。

这种快照方式违背了Raft的强leader原则，因为follower可以在不知道leader的情况下进行快照。然而，我们认为这一违背是合理的。拥有一个leader在达成共识时避免决策冲突，在快照时共识已经达成，所以没有决策冲突。数据仍然仅从leader流向follower，只有follower现在能重组它的数据。

我们考虑一个 基于leader的只有leader可以创建快照的 替代方案，然后它可以给每一个follower发送快照。然而，这有两个缺点。首先，给每个follower发送快照浪费网络带宽，减慢快照过程。每个follower已经有需要用于生成他自己快照的数据，通常 server用本地状态生成快照 比 通过网络发送和接收一个 成本更低。其次，leader的实现会更复杂。例如，leader会需要 通过备份新的日志条目 并行地发送快照给follower，以免阻塞新的client请求。

有两个问题影响快照的性能。第一，server必须决策什么时候进行快照。如果一个server太频繁快照，它会浪费磁盘带宽和能力；如果它快照太不频繁，就会有耗尽它存储的风险，也会增加重启后重放日志需要的时间。一个简单的进行快照的策略是，当日志达到一定大小，就快照。如果这个大小被设置为显著大于快照的预期大小，那么快照的磁盘带宽消耗会很小。

第二个性能问题是，写快照会花费很长时间，我们不希望这回推迟正常操作。解决方法是使用copy-on-write技术，这样新的更新可以在不影响写快照的情况下处理。例如，状态机构建原声支持这种能力的功能性数据结构。或者，操作系统的copy-on-write支持（例如，Linux的fork）可以用来创建一个整个状态的内存快照（我们的实现使用这种方法）。

## 8. client交互

这一节描述client如何跟Raft交互，包括 client如何找到集群leader，Raft如何支持线性化语义（linearizable semantics）。这些问题适用于所有基于共识的系统，Raft的解决方案也跟其他系统类似。

Raft的client向leader发送所有的请求。当一个client第一次发送时，它随机选一个server联系。如果client第一次选的不是leader，那个server会拒绝client的请求，并提供它最近听说的leader的信息（AppendEntries请求包含leader的网络地址）。如果leader crash，client请求会超时；client随后随机选server重试。

我们Raft的目标是实现线性化语义（每个操作在它被调用和应答之间，看上去会理解执行，并确切一次）。然而，到目前位置的描述，Raft可能多次执行一个操作；例如，如果leader在commit日志条目后但是在应答给client之前crash，client会向新leader重试这个命令，导致这个命令会执行两次。解决方案是，client给每个命令分配唯一序列号。然后，状态机维护每个client最新处理的序列号，以及与之相关的应答。如果他收到已经处理过的命令的序列号，他就无需重新直接，可以立即返回。

只读操作可以不用往日志写任何东西就处理完成。然而，没有额外措施，这会有返回陈旧数据的风险，因为响应请求的leader可能已经被它不知道的新leader所取代。线性化读必须不会返回陈旧数据，Raft需要两个额外预防措施来在不写日志的情况下保证这一点。首先，leader必须有 哪些条目已committed的 最新信息。Leader Completeness Property保证leader有所有committed的条目，但是在他的term开始的时候，他也许不能哪些已committed。为了确认，他需要commit一个它的term的条目。Raft通过让leader在他term开始的时候commit一个空no-op条目到日志来处理这个问题。其次，leader必须在处理只读操作前确认它是否被罢免了（如果有新的leader，它的信息可能已经落后了）。Raft通过让leader响应只读请求前 给集群的大多数交换心跳消息 来处理这个问题。或者，leader可以依赖心跳机制，提供一种形式的租约，但这会让安全性依赖于timing（这假设有限的时钟偏差）。

## 9. 实现和评估

这里没什么好翻译的。。。可以看下原文

### 9.3 性能

## 10. 相关工作

## 11. 总结

算法总是以 正确性、有效性、简明 为关键目标设计。虽然这些都是有价值的目标，我们认为可理解性也一样重要。在开发者实际实现算法前以上任何目标都无法达成，这样不可避免的 偏离与/扩展 算法的出版形式。除非开发者对算法有深刻理解、能对它产生直观理解，他们很难在实现中保留算法的合理的属性。

在这片文章中，我们处理分布式算法的问题，一个广泛接受但是令人费解的算法，Paxos，它在许多年间一直困扰这学生和开发者。我们开发一个新的算法，Raft，比Paxos更容易理解。我们也相信，Raft为系统构建提供一个更好的基础。以可理解性为首要目标，改变了我们完成Raft设计的方法；随着设计进程推进，我们不断发现我们服用着一些技术，例如分解问题和简化状态空间。这些技术，不仅提高了Raft的可理解性，也是我们相信它的正确性。
