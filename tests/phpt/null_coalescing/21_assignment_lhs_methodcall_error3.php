@kphp_should_fail
/Function calls on the left-hand side of \?\?= are not supported/
<?php

class A {
    /** @var ?int */
    public $x = null;

    public function next() : A {
      return null;
    }
}

$a = [new A(), new A()];

$a[0]->next()->x ??= 99;
