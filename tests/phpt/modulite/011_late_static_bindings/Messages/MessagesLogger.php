<?php

namespace Messages;

use Engines\Logs\BaseLog;

class MessagesLogger extends BaseLog {

  public static function create(): void {
    parent::createLog();
  }

  public static function log(): void {
    parent::logAction();

  }
}