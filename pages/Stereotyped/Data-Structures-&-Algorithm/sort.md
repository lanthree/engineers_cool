# 排序

## 插入排序

插入排序由N-1此插入组成，对于第i趟，把下标i的数字插入到下标0~i的合适位置。时间复杂度O(n^2)。

```cpp
template <typename Comparable>
void insertionSort(std::vector<Comparable>& v) {
  int j;
  for (int p = 1; p < v.size(); p++) {
    Comparable tmp = v[p];
    for (j = p; j > 0 && tmp < v[j - 1]; j--) {
      v[j] = v[j - 1]; 
    }   
    v[j] = tmp;
  }
}
```

可能的STL实现：

```cpp
template <typename Iterator, typename Comparator, typename Object>
void _insertionSort(const Iterator& begin, const Iterator& end, Comparator lessThan, const Object& obj) {
  Iterator j;
  for (Iterator p = begin + 1; p != end; ++p) {
    Object tmp = *p; 
    for (j = p; j != begin && lessThan(tmp, *(j - 1)); --j) {
      *j = *(j - 1); 
    }   
    *j = tmp;
  }
}

template <typename Iterator, typename Comparator>
void insertionSort(const Iterator& begin, const Iterator& end, Comparator lessThan) {
  if (begin != end) _insertionSort(begin, end, lessThan, *begin);
}

template <typename Iterator, typename Object>
void _insertionSortHelp(const Iterator& begin, const Iterator& end, const Object& obj) {
  insertionSort(begin, end, less<Object>());
}

template <typename Iterator>
void insertionSort(const Iterator& begin, const Iterator& end) {
  if (begin != end) _insertionSortHelp(begin, end, *begin);
}
```

## 谢尔排序

通过多趟比较相距一定间隔的蒜素来工作：各趟比较所用的间隔随着算法的进行而减小，直到只比较相邻元素的最后一趟为止。谢尔也叫**缩减增量排序**。

谢尔排序使用一个序列 h1,h2,...hi，叫做**增量序列**。只要`h1=1`，任何增量序列都可以。不过，有些增量序列比另外一些增量序列更好。

使用谢尔增量的排序，时间复杂度O(n^2)。

```cpp
template <typename Comparable>
void shellSort(std::vector<Comparable>& v) {
  for (int gap = v.size() / 2; gap > 0; gap /= 2)
    for (int p = gap; p < v.size(); ++p) {
      Comparable tmp = v[p];
      int j = p;
      for (; j >= gap && tmp < v[j - gap]; j -= gap) {
        v[j] = v[j - gap];
      }   
      v[j] = tmp;
    }   
}
```
