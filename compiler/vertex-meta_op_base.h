#pragma once

#include "compiler/data_ptr.h"
#include "compiler/type-inferer-core.h"

template<Operation Op>
vertex_inner<Op> *raw_create_vertex_inner(int args_n);

template<>
class vertex_inner<meta_op_base> {
public:
  typedef VertexPtr value_type;
  typedef value_type *xiterator;
  typedef const value_type *const_xiterator;
  typedef std::reverse_iterator<xiterator> iterator;
  typedef std::reverse_iterator<const_xiterator> const_iterator;

private:
  Operation type_;
  int n;
public:
  int id;
  tinf::ExprNode tinf_node;
  VertexPtr type_rule;
  Location location;

  OperationExtra extra_type : 4;
  PrimitiveType type_help : 5;
  RLValueType rl_type : 2;
  RLValueType val_ref_flag : 2;
  ConstValueType const_type : 2;
  int ref_flag : 1;
  bool auto_flag : 1;
  bool varg_flag : 1;
  bool throws_flag : 1;
  union {
    bool resumable_flag : 1;
    bool fork_flag : 1;
  };
  bool parent_flag : 1;
  bool needs_const_iterator_flag : 1;
  bool inline_flag : 1;
  bool void_flag : 1;

private:
  VertexPtr *arr() const {
    return (VertexPtr *)this - 1;
  }

protected:

  bool check_range(int i) const { return 0 <= i && i < size(); }

  VertexPtr &ith(int i) {
    assert (check_range(i));
    return arr()[-i];
  }

  const VertexPtr &ith(int i) const {
    assert (check_range(i));
    return arr()[-i];
  }

  template<class... Args>
  void set_children(int shift, VertexPtr arg, Args &&... args) {
    ith(shift) = arg;
    set_children(shift + 1, std::forward<Args>(args)...);
  }

  template<class... Args>
  void set_children(int shift, const std::vector<VertexPtr> &arg, Args &&... args) {
    for (int i = 0, ni = (int)arg.size(); i < ni; i++) {
      ith(shift + i) = arg[i];
    }
    set_children(shift + (int)arg.size(), std::forward<Args>(args)...);
  }

  void set_children(int shift) {
    dl_assert(shift == n, "???");
  }

  template<class... Args>
  static int get_children_size(const VertexPtr &, Args &&... args) {
    return 1 + get_children_size(std::forward<Args>(args)...);
  }

  template<class... Args>
  static int get_children_size(const std::vector<VertexPtr> &arg, Args &&... args) {
    return (int)arg.size() + get_children_size(std::forward<Args>(args)...);
  }

  static int get_children_size() {
    return 0;
  }


public:
  vertex_inner() :
    type_(op_none),
    n(-1),
    id(0),
    tinf_node(VertexPtr(this)),
    type_rule(),
    location(),
    extra_type(op_ex_none),
    type_help(),
    rl_type(val_error),
    val_ref_flag(val_none),
    const_type(cnst_error_),
    ref_flag(0),
    auto_flag(),
    varg_flag(),
    throws_flag(),
    resumable_flag(),
    parent_flag(),
    needs_const_iterator_flag(),
    inline_flag(),
    void_flag() {
  }

  vertex_inner(const vertex_inner<meta_op_base> &from) :
    type_(from.type_),
    n(-1),
    id(from.id),
    tinf_node(VertexPtr(this)),
    type_rule(from.type_rule),
    location(from.location),
    extra_type(from.extra_type),
    type_help(from.type_help),
    rl_type(from.rl_type),
    val_ref_flag(from.val_ref_flag),
    const_type(from.const_type),
    ref_flag(from.ref_flag),
    auto_flag(from.auto_flag),
    varg_flag(from.varg_flag),
    throws_flag(from.throws_flag),
    resumable_flag(from.resumable_flag),
    parent_flag(from.parent_flag),
    needs_const_iterator_flag(from.needs_const_iterator_flag),
    inline_flag(from.inline_flag),
    void_flag(from.void_flag) {
  }

  virtual ~vertex_inner() {}

  void copy_location_and_flags(const vertex_inner<meta_op_base> &from) {
    type_rule = from.type_rule;
    location = from.location;
    val_ref_flag = from.val_ref_flag;
    const_type = from.const_type;
    ref_flag = from.ref_flag;
    auto_flag = from.auto_flag;
    varg_flag = from.varg_flag;
    throws_flag = from.throws_flag;
    resumable_flag = from.resumable_flag;
    parent_flag = from.parent_flag;
    needs_const_iterator_flag = from.needs_const_iterator_flag;
    inline_flag = from.inline_flag;
    void_flag = from.void_flag;
  }

  void raw_init(int real_n) {
    assert (n == -1);
    n = real_n;
    for (int i = 0; i < n; i++) {
      new(&ith(i)) VertexPtr();
    }
  }

  void raw_copy(const vertex_inner<meta_op_base> &from) {
    assert (n == -1);
    n = from.size();
    for (int i = 0; i < n; i++) {
      new(&ith(i)) VertexPtr(from.ith(i).clone());
    }
  }

  int size() const { return n; }

  VertexPtr &back() { return ith(size() - 1); }

  vector<VertexPtr> get_next() { return vector<VertexPtr>(begin(), end()); }

  bool empty() { return size() == 0; }

  iterator begin() { return iterator(arr() + 1); }

  iterator end() { return iterator(arr() - size() + 1); }

  const_iterator begin() const { return const_iterator(arr() + 1); }

  const_iterator end() const { return const_iterator(arr() - size() + 1); }

  const Location &get_location() { return location; }

  void init() {}

  static void init_properties(OpProperties *p __attribute__((unused))) {}

  const Operation &type() const { return type_; }

  const char *get_c_string() const { return get_string().c_str(); }

  virtual const FunctionPtr &get_func_id() const { dl_fail ("get_func_id is not supported"); }

  virtual void set_func_id(FunctionPtr func_ptr __attribute__((unused))) { dl_fail ("set_func_id is not supported"); }

  virtual const VarPtr &get_var_id() const { dl_fail (dl_pstr("not supported [%d:%s]", type_, OpInfo::str(type_).c_str())); }

  virtual void set_var_id(const VarPtr &) { dl_fail (dl_pstr("not supported [%d:%s]", type_, OpInfo::str(type_).c_str())); }

  virtual const string &get_string() const { dl_fail (dl_pstr("not supported [%d:%s]", type_, OpInfo::str(type_).c_str())); }

  virtual void set_string(const string &) { dl_fail (dl_pstr("not supported [%d:%s]", type_, OpInfo::str(type_).c_str())); }

  virtual bool has_get_string() const { return false; }

  template<Operation Op>
  friend vertex_inner<Op> *raw_create_vertex_inner(int args_n);

  template<typename... Args>
  static vertex_inner<meta_op_base> *create(Args &&... args) {
    vertex_inner<meta_op_base> *v = raw_create_vertex_inner<meta_op_base>(get_children_size(std::forward<Args>(args)...));
    v->set_children(0, std::forward<Args>(args)...);
    return v;
  }

};

using Vertex = vertex_inner<meta_op_base>;
using VertexRange = vk::iterator_range<Vertex::iterator>;
using VertexConstRange = vk::iterator_range<Vertex::const_iterator>;
