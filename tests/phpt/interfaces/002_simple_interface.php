@ok
<?php

require_once("polyfills.php");

$a = new Classes\A();
$b = new Classes\B();

$a->do_it(10, 20);
$b->do_it(1000, 2000);
