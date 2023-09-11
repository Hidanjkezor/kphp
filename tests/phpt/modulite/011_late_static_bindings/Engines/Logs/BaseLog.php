<?php

namespace Engines\Logs;

abstract class BaseLog {
  protected static function logAction(): bool {
    return true;
  }

  protected static function createLog(): void {
  }
}



