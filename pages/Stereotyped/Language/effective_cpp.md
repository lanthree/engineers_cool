# Effective C++

## 条款01：视C++为一个语言联邦

+ C：C++以C为基础，区块（blocks）、语句（statements）、预处理器（preprocessor）、内置数据类型（built-in data types）、数据（arrays）、指针（pointers）等统统来自C。
+ Object-Oriented C++：这部分也就是C with Classes所诉求的，classes（包括构造函数和析构函数），封装（encapsulation）、继承（inheritance）、多态（polymorphism）、virtual函数（动态绑定）……等等。
+ Template C++：这是C++的泛型编程（generic programming）部分，它们带来崭新的编程范型（prpgramming paradigm），也就是所谓的template metaprogramming（TMP，模版元编程）。
+ STL：STL是个template程序库。

请记住：
+ C++高效编程守则视状况而变化，取决于你使用C++的哪一部分。

## 条款02：尽量以const，enum，inline替换#define

以常量替换`#define`：
1. 定义常量指针（constant pointers），如果要在头文件内定义一个常量的（不变的）`char*-bases`字符串，必须写`const`两次：
    + `const char* const authorName = "Scott Meyers";`
    + 或者写成`const std::string authorName("Scott Meyers");`
2. class专属常量
    + ```cpp
      // static class 常量声明位于头文件内
      class CostEstimate {
       private:
        static const double FudgeFactor;
        ...
      };

      // static class常量定义位于实现文件内
      const double CostEstimate::FudgeFactor = 1.35;
      ```

enum hack：一个属于枚举类型（enumerated type）的数值可权充ints被使用

```cpp
class GamePlayer {
 private:
  enum {NumTurns = 5};

  int scores[NumTurns];
  ...
};
```

宏函数可以用template inline函数替代：
```cpp
#define CALL_WITH_MAX(a, b) f((a) > (b) ? (a) : (b))

// 但会有一些不符合预期的事情
int a = 5, b = 0;
CALL_WITH_MAX(++a, b);    // a被累加两次
CALL_WITH_MAX(++a, b+10); // a被累加一次

// 替代函数
template<typename T>
inline void callWithMax(const T& a, const T& b) {
  f(a > b ? a : b);
}
```

请记住：
+ 对于单纯常量，最好以const对象或enums替换`#define`。
+ 对于形似函数的宏（macros），最好改用inline函数替换

## 条款03：尽可能使用const

如果关键字const出现在星号的左边，表示被指物是常量；如果出现在星号右边，表示指针自身是常量；如果出现在星号两边，表示被指物和指针两者都是常量。

const迭代器：
```cpp
std::vector<int> vec;

// iter的作用像个T* const
const std::vector<int>::iterator iter = vec.begin();
*iter = 10;  // 没问题
++iter;      // 不可以

// cIter的作用像个const T*
std::vector<int>::const_iterator cIter = vec.begin();
*cIter = 10; // 不可以
++cIter;     // 没问题
```

在一个函数声明式内，const可以和函数返回值、各参数、函数自身（（如果是成员函数）产生关联。

成员函数如果是const意味着什么？这有两个流行概念：bitwise constness（又称physical constness）和logical constness。

前者是说它不更改对象内的任何一个bit，也是C++对常量性（constness）的定义，即const成员函数不可以更改对象内任何non-static成员变量。但如果该变量是指针，指针指向的内容不在约束之内。

后者主张，一个const成员函数可以修改它所处理的对象内的某些bits，但只有在客户端侦测不出的情况下才得如此，即保证逻辑上的常量性 但实际可以修改某些bits（通过`mutable`释放掉non-static成员变量的bitwise constness约束）：

```cpp
class CTextBlock {
 public:
  ...
  std::size_t length() const;
 private:
  char* pText;
  mutable std::size_t textLength;
  mutable bool lengthIsValid;
};

std::size_t CTextBlock::length() const {
  if (!lengthIsValid) {
    textLength = std::strlen(pText);
    lengthIsValid = true;
  }
  return textLength;
}
```

如果你需要实现const和non-const成员函数，那么可能会有大段的重复代码（只有函数和返回值的const修饰不同），如果代码确实一样，可以考虑用const版本实现non-const版本：

```cpp
class TextBlock {
 public:
  ...
  const char& operator[](std::size_t p) const {
    ...
    return text[p];
  }

  char& operator[](std::size_t p) {
    // 将op[]返回值的const移除
    return const_cast<char&> (
      // 为*this加上const调用const op[]
      static_cast<const TextBlock&>(*this)[p]
    );
  }
  ...
};
```

反过来，令const版本调用non-const版本以避免重复是一种错误行为。

请记住：

+ 将某些东西声明为const可帮助编译器侦测出错误用法。const可被施加于任何作用域内的对象、函数参数、函数返回类型、成员函数本体。
+ 编译器强制实施bitwise constness，但你编写程序时应该使用“概念上的常量性”（conceptual constness）。
+ 当const和non-const成员函数有着实质等价的实现时，令non-const版本调用const版本可避免代码重复。

## 条款04：确定对象被使用前已被初始化

永远在适用对象之前先将它初始化，处于无任何成员的内置类型，你必须手工完成此事。至于内置类型意外的任何其他东西，初始化责任落在构造函数（constructors）身上。

C++有着十分固定的“成员初始化次序”，次序总是相同：base classes更遭遇其dervied class被初始化，而class的成员变量总是以其声明次序被初始化。

不同编译器单元内定义之non-local static对象的初始化次序：

所谓static对象，其寿命从被构造出来知道程序结束为止，包括global对象、定义于namespace作用域内的对象、在classes内、在函数内、以及在file作用域内被声明为static的对象。函数内的static对象称为non-local static对象；其他static对象称为non-local static对象。程序结束时static对象会被自动销毁，也就是他们的析构函数会在`main()`结束时被自动调用。

所谓编译单元（translation unit）是指产出单一目标文件（single object file）的那些源码。

如果某编译单元内的某个non-local staic对象的初始化动作使用了另一个编译单元内的某个non-local static对象，它所用到的这个对象可能尚未被初始化，因为C++对“定义于不同编译单元内的non-local static对象”的初始化次序并无明确定义。

解决方案：将每个non-local static对象搬到自己的专属函数内（该对象在此函数内被声明为static）（refrence-returning）。C++保证，函数内的local static对象会在“该函数被调用期间”“首次遇上该对象之定义式”时被初始化。

```cpp
class FileSystem { ... };
// 这个函数用来替换全局tfs对象
FileSystem &tfs() {
  static FileSystem fs;
  return fs;
}

class Directory { ... };
Directory::Director(params) {
  ...
  std::size_t disks = tfs().numDisks();
  ...
}
// 这个函数用来替换全局tempDir对象
Directory& tempDir() {
  static Directory td;
  return td;
}
```
为了消除与初始化有关的“竞速形势”（race conditions），可在程序的单线程启动阶段（single-threaded startup portion）手工调用所有reference-returning函数。

请记住：
+ 为内置对象进行手工初始化，因为C++不保证初始化它们。
+ 构造函数最好使用成员初值列（member intialization list），而不要在构造函数本体内使用赋值操作（assignment）。初值列列出的成员变量，其排列次序应该和它们在class中的声明次序相同。
+ 为免除“跨编译单元之初始化次序”问题，请以local static对象（reference-returning）替换non-local static对象。

## 条款05：了解C++默默编写并调用哪些函数

如果你自己没声明，编译器就会为class声明一个copy构造函数、一个copy assignment操作符和一个析构函数。此外，如果你没有声明任何构造函数，编译器也会为你声明一个default构造函数。左右这些函数都是public且inline：

```cpp
class Empty {};
// 等价于
class Empty {
 public:
  Empty() {...}  // defualt构造函数
  Empty(const Empty& rhs) {...} // copy构造函数
  ~Empty() {...} // 析构函数

  Empty& operator=(const Empty& rhs) {...} // copy assignment操作符
};
```
> 唯有当这些函数被需要（被调用），它们才会被编译器创建出来。

注意，如果你打算在一个“内含reference成员”/“内含const成员”的class内置支持赋值操作（assignment），你必须自己定义copy assignment操作符。另外，如果某个base classes将copy assignment操作符声明为private，编译器将拒绝为其derived classes生成一个copy assignment操作符。

请记住：
+ 编译器可以暗自为class创建default构造函数、copy构造函数、copy assignment操作符、以及析构函数。

## 条款06：若不想使用编译器自动生成的函数，就该明确拒绝

请记住：
+ 为驳回编译器自动（暗自）提供的机能，可将相应的成员函数声明为private并且不予实现（c++11开始还可以使用delete修饰）。使用像Uncopyable这样的base class也是一种做法。

## 条款07：为多态基类声明virtual析构函数

请记住：
+ polymorphic（带有多态性质的）base classes应该声明一个virtual析构函数。如果class带有任何virtual函数，他就应该拥有一个virtual析构函数。
+ classes的设计目的如果不作为base classes使用，或不是为了具备多态性（polymorphically），就不该声明virtual析构函数。

## 条款08：别让异常逃离析构函数

C++并不禁止析构函数吐出异常，但它不鼓励你这样做。如果在析构函数中的确有操作可能抛出异常，可以有两种方法避免：

第一种方法，在析构函数内消化掉异常：

```cpp
class DBConn {
 public:
  ...
  ~DBConn() {
    try { db.close(); }
    catch (...) {
      // abort程序：std::abort()
      // 或者 忽略
    }
  }
 private:
  DBConnection db;
};
```

另外一种方法是提供一个新函数，供调用方可以处理异常：

```cpp
class DBConn {
 public:
  ...
  void close() { // 提供的新函数
    db.close();
    closed = true;
  }
  ~DBConn() {
    if (closed) return;

    try { db.close(); }
    catch (...) {
      ...
    }
  }
 private:
  DBConnection db;
  bool closed;
};
```

请记住：
+ 析构函数绝对不要吐出异常。如果一个被析构函数调用的函数可能抛出异常，析构函数应该捕捉任何异常，然后吞下它们（不传播）或结束程序。
+ 如果客户需要对某个操作函数运行期间抛出的异常做出反应，那么class应该提供一个普通函数（而非在析构函数中）执行该操作。

## 条款09：绝不在构造和析构过程中调用virtual函数

请记住：
+ 在构造和析构期间不要调用virtual函数，因为这类调用从不下降至derived class（比起当前执行构造函数和析构函数的那层）。

## 条款10：令operator=返回一个reference to *this

为了实现“连锁赋值”，赋值操作符必须返回一个reference指向操作符的左侧实参：

```cpp
class Widget {
 public:
  Widget& operator+=(const Widget& rhs) {
    ...
    return *this;
  }
  Widget& operator=(const Widget& rhs) {
    ...
    return *this;
  }
  ...
};
```

请记住：
+ 令赋值（assignment）操作符返回一个reference to *this。

## 条款11：在operator=中处理“自我赋值”

证同测试（identify test）：

```cpp
Widget& Widget::operator=(const Widget& rhs) {
  if (this == &rhs) return *this;

  delete pb; // Bitmap* Widget::pb;
  pb = new Bitmap(*rhs.pb);
  return *this;
}
```

为了防止在`new`出现异常导致Widget不可用，可以先不删除：

```cpp
Widget& Widget::operator=(const Widget& rhs) {
  Bitmap* pOrig = pb;
  pb = new Bitmap(*rhs.pb);
  delete pOrig;
  return *this;
}
```

另一个替代方案是`copy-and-swap`：

```cpp
void Widget::swap(Widget& rhs) {
  ...
}
Widget& Widget::operator=(const Widget& rhs) {
  Widget tmp(rhs);
  swap(temp);
  return *this;
}
```

考虑到，如果copy assignment操作符声明的参数如果不是引用，那么以by value方式传递时就会创造一个副本，可以直接拿来swap：

```cpp
void Widget::swap(Widget& rhs) {
  ...
}
Widget& Widget::operator=(const Widget rhs) {
  swap(rhs);
  return *this;
}
```

请记住：
+ 确保当对象自我赋值时 operator= 有良好行为。其中技术包括 比较“来源对象”和“目标对象”的地址、精心周到的语句顺序、以及`copy-and-swap`。
+ 确定任何函数如果操作一个以上的对象，而其中多个对象是同一个对象时，其行为仍然正确。

## 条款12：复制对象时勿忘其中每一个成分

任何时候，只要你承担起“为derived class撰写copying函数”（copy构造函数、copy assignment操作符）的重责大任，必须很小心地也复制其base class成分：

```cpp
Dervied::Dervied(const Dervied& rhs)
  : Base(rhs), dervied_v(rhs.dervied_v)
{}

Dervied& Dervied::operator=(const Dervied& rhs) {
  Base::operator=(rhs);
  dervied_v = rhs.dervied_v;
  return *this;
}
```

请记住：
+ copying函数应该确保复制“对象内的所有成员变量”及“所有base class成分”。
+ 不要尝试以某个copying函数实现另一个copying函数。应该将共同机能放进第三个函数中，并由两个copying函数共同调用。

## 条款13：以对象管理资源

+ 获得资源后立刻放进管理对象（managing object）内。“以对象管理资源”的观念常被称为“资源取得时机便是初始化时机”（Resource Acquisition Is Initialization；RAII）。
+ 管理对象（managing object）运用析构函数确保资源被释放。

请记住：
+ 为防止资源泄漏，请使用RAII对象，它们在构造函数中获得资源并在析构函数中释放资源。

## 条款14：在资源管理类中小心copying行为

假设你自己为mutex实现了一个RAII类：

```cpp
class Lock {
 public:
  explicit Lock(Mutex* pm) : mutexPtr(pm)
  {
    lock(mutexPtr);
  }
  ~Lock() { unlock(mutexPtr); }
};
```

如果Lock对象发生复制，默认的行为很槽糕。大多数时候你会选择一下两种可能：

+ 禁止复制。
+ 对底层资源祭出“引用计数法”（reference-count）。

请记住：
+ 复制RAII对象，必须一并复制它所管理的资源，所以资源的copying行为决定RAII对象的copying行为
+ 普遍而常见的RAII class copying行为是：抑制copying、施行引用计数法（reference counting）。不过其他行为（复制底部资源、转移底部资源的所有权）也都可能被实现。

## 条款15：在资源管理类中提供对原始资源的访问

显示转换：提供`get()`函数，拿到底层资源

隐士转换：提供隐士转换函数

```cpp
class Font {
public:
 ...
 operator FontHandle() const // 隐士转换函数
 {return f;}
 ...
private:
 FontHandle f;
};

Font f1(getFount()); // RAII
FontHandle f2 = f1;  // f1隐士转换为其底层的FontHandle然后才复制它
```

请记住：
+ APIs往往要求访问原始资源（raw resources），所以每一个RAII class应该提供一个“取得其所管理之资源”的办法。
+ 对原始资源的访问可能经由 显式转换 或 隐式转换。一般而言显式转换比较安全，但隐式转换对客户比较方便。

## 条款16：成对使用new和delete时要采取相同的形势

当使用new（也就是通过new动态生成一个对象），有两件事发生。第一，内存被分配出来（通过名为`operator new`的函数）。第二，针对此内存会有一个（或更多）构造函数被调用。

当使用delete，也有两件事发生：针对此内存会有一个（或更多）析构函数被调用，然后内存才被释放（通过名为`operator delete`的函数）。

请记住：
+ 如果你在new表达式中使用`[]`，必须在相应的delete表达式中也使用`[]`；如果不在new表达式中不实用`[]`，一定不要在相应的delete表达式中使用`[]`。

## 条款17：以独立语句将newed对象置入智能指针

假设有如下代码

```cpp
int priority();
void process(std::shared_ptr<Widget> pw, int priority);

process(std::shared_ptr<Widget>(new Widget), priority());
```

上述代码可能以以下顺序执行（编译优化导致顺序不定）：
1. 执行`new Widget`
2. 调用`priority()`
3. 调用`std::shared_ptr`构造函数

若在`priority()`发生异常，那么将会造成资源泄漏。避免这类问题的方法，是使用分离语句：

```cpp
std::shared_ptr<Widget> pw(new Widget);
process(pw, priority());
```

请记住：
+ 以独立语句将newed对象存储于（置入）智能指针内。如果不这样做，一旦异常被抛出，有可能导致难以察觉的资源泄漏。

## 条款18：让接口容易被正确使用，不易被误用

理想上，如果客户企图使用某个接口而却没有获得他所预期的行为，这个代码不应该通过编译；如果代码通过了编译，它的作为就该是客户所想要的。

请记住：
1. 好的接口很容易被正确使用，不容易被误用。你应该在你的所有接口中努力达成这些性质。
2. “促进正确使用”的办法包括接口的一致性，以及与内置类型的行为兼容。
3. “阻止误用”的办法包括建立新类型、限制类型上的操作，束缚对象值，以及消除客户的资源管理责任。
4. `std::shared_ptr`支持定制型删除器（custom deleter）。这可防范DLL问题，可被用来自动解除互斥锁（mutexes）等等。

## 条款19：设计class犹如设计type

你应该带着和“语言设计者当初设计语言内置类型时”一样的谨慎来研讨class的设计。

设计高效的class需要面对的问题：
+ 新type的对象应该如何被创建和销毁？
+ 对象的初始化和对象的赋值该有什么样的差别？
+ 新type的对象如果被`pass-by-value`以值传递），意味着什么？
    + copy构造函数用来定一个type的`pass-by-value`如何实现
+ 什么是新type的“合法值”？
+ 你的新type需要配合某个继承图系（inheritance graph）吗？
+ 你的新type需要什么样的转换？
+ 什么样的操作符和函数对此新type而言是合理的？
+ 什么样的标准函数应该驳回？（= delete）
+ 谁该取用新type的成员？
+ 什么是新type的“未声明接口”（undeclared interface）？
+ 你的新type有多么一般化？（class template？）
+ 你真的需要一个新type吗？

请记住：
+ class的设计就是type的设计。在定义一个新type之前，请确定你已经考虑过本条款覆盖的所有讨论主题。

## 条款20：宁以pass-by-reference-to-const替换pass-by-value

请记住：
+ 尽量以`pass-by-reference-to-const`替换`pass-by-value`。前者通常比较高效，并可避免切割问题（slicing problem）。
+ 以上规则并不设用于内置类型，以及STL的迭代器和函数对象。对它们而言，`pass-by-value`往往比较何时。

## 条款21：必须返回对象时，别妄想返回其reference

当你必须在“返回一个reference和返回一个object”之间抉择时，你的工作就是挑出行为正确的那个。

请记住：
+ 绝不要返回pointer或reference指向一个local stack对象，或返回reference指向一个heap-allocated对象，或返回pointer或reference指向一个local static对象而有可能同时需要多个这样的对象。

## 条款22：将成员变量声明为private

请记住：
+ 切记将成员变量声明为private。这可赋予客户访问数据的一致性、可细微划分访问控制、允许约束条件获得保证，并提供class作者以充分的实现弹性。
+ protected并不比public更具封装行。

## 条款 23：宁以non-member、non-friend替换member函数

愈多东西被封装，我们改变那些东西的能力也就愈大。这就是我们首先推崇封装的原因：它使我们能够改变事物而只影响有限的客户。

考虑对象内的数据，愈少代码可以看到数据（也就是访问它），愈多的数据可被封装，而我们也就愈能自由地改变对象数据。

请记住：
+ 宁可拿non-member non-friend函数替换member函数。这样做可以增加封装性、包裹弹性（packaging flexibility）和机能扩充性。

## 条款24：若所有参数接续类型转换，请为此采用non-member函数

假设有类`Rational`：

```cpp
class Rational {
 public:
  // 可以不为explicit：允许int-to-Rational隐式转换
  Rational(int numerator = 0,
           int demoninator = 1);
  int numerator() const;
  int demoninator() const;
 private:
  ...
};
```

此时想支持乘法操作，加入该操作定义放到函数内：

```cpp
class Rational {
 public:
  ...
  const Rational operator* (const Rational& rhs) const;
};
```

现在可以做Rational与Rational的乘法，假设还想做int与Rational的乘法：

```cpp
Rational oneHalf(1, 2);
Rational result_1 = oneHalf * 2; // 可以，2隐式转换
Rational result_2 = 2 * oneHalf; // 不可以
```
`2 * oneHalf`尝试找`2.operator*(oneHalf)`与全局的`operator*(2, oneHalf)`但是都没有。那么，一个支持混合运算的方法，就是声明为全局操作函数：

```cpp
class Rational {
 public:
  ...
};

const Rational operator* (
    const Rational& lhs, const Rational& rhs) {
  return Rational(lhs.numerator() * rhs.numerator(),
                  lhs.demoninator() * rhs.demoninator());
}
```

> 当从Object-Oriented C++转进入Template C++并让Rational成为一个class template而非class，又有一些需要考虑的新争议、新接发。

请记住：
+ 如果你需要为某个函数的所有参数（包括被this指针所指的那个隐于参数）进行类型转换，那么这函数必须是个non-member。

## 条款25：考虑写出一个不抛异常的swap函数

所谓swap（置换）两个对象值，意思是将两对象的值彼此赋予多方。缺省情况下swap动作可由标准程序提供的swap算法完成。其典型实现完全如你所预期：

```cpp
namespace std {
template<typename T>
void swap(T& a, T& b) {
  T temp(a);
  a = b;
  b = temp;
}
}
```

只要类型T支持copying，缺省的swap实现代码就会帮你置换类行为T的对象，你不需要为此另外再做任何工作。

假设如果需要swap一个pimpl（pointer to implementation）的类对象：

```cpp
class WidgetImpl {
 public:
  ...
 private:
  int a, b, c;           // 可能有许多数据
  std::vector<double> v; // 意味复制时间很长
};

class Widget { // 这个class使用pimpl手法
 public:
  Widget(const Widget& rhs);
  // 复制Widget时，令它复制其WidgetImpl对象
  Widget& operator=(const Widget& rhs) {
    ...
    *pImpl = *(rhs.pImpl);
    ...
  }
  ...
 private:
  WidgetImpl* pImpl;
};
```

理论上，如果要swap这两个，只需要置换其中的指针即可，但上面的的swap函数会连`WidgetImpl`也做置换（因为Widget的实现）。此时，我们可以特化`std::swap`：

```cpp
class Widget {
 public:
  ...
  void swap(Widget& other) {
    std::swap(pImpl, other.pImpl);
  }
  ...
};

namespace std {
template<> // 表示全特化total template specialization
// 特化std::swap
void swap<Widget>(Widget& a, Widget& b) {
  a.swap(b);
}
}
```

如果Widget、WidgetImpl是class template的话，因为C++不允许偏特化（partially specialize）一个function template（std::swap）。重载可以解决这种问题，但是重载std函数，不可行。

可以在私有的命名空间内定义一个swap函数：

```
namespace WidgetStuff {
template<typename T>
class Widget {...};
...

// 这里不属于std命名空间
template<typename T>
void swap(Widget<T>& a, Widget<T>& b) {
  s.swap(b);
}
}
```

C++的名称查找法则（name lookup rules）确保将找到global作用域或`Widget`所在之命名空间内的任何Widget专属的swap，并使用“实参取决之查找规则”（argument-dependent lookup）找出`WidgetStuff`内的swap。

总结之，如果std::swap的缺省实现，效率可接受，你不需要额外做任何事。如果缺省实现的版本效率不足，试着做以下事情：

1. 提供一个public swap成员函数，让它高效地置换你的类型的两个对象值。这个函数绝不该抛出异常。
2. 在你的class或template所在的命名空间内提供一个non-member swap，并令它调用上述swap成员函数。
3. 如果你正编写一个class（而非class template），为你的class特化std::swap。并令它调用你的swap成员函数

请记住：
+ 当`std::swap`对你的类型效率不高时，提供一个swap成员函数，并确定这个函数不抛出异常。
+ 如果你提供一个member swap，也该提供一个non-member swap用来调用前者。对于classes（而非templates），也请特化`std::swap`。
+ 调用swap时应针对`std::swap`使用using声明式，然后调用swap并且不带任何“命名空间资格修饰”。
+ 为“用户定义类型”进行std templates全特化是好的，但千万不要尝试在std内加入某些对std而言全新的东西。

