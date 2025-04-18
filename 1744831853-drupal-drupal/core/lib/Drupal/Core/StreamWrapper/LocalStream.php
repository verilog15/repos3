<?php

namespace Drupal\Core\StreamWrapper;

/**
 * Defines a Drupal stream wrapper base class for local files.
 *
 * This class provides a complete stream wrapper implementation. URIs such as
 * "public://example.txt" are expanded to a normal filesystem path such as
 * "sites/default/files/example.txt" and then PHP filesystem functions are
 * invoked.
 *
 * Drupal\Core\StreamWrapper\LocalStream implementations need to implement at
 * least the getDirectoryPath() and getExternalUrl() methods.
 */
abstract class LocalStream implements StreamWrapperInterface {
  /**
   * Stream context resource.
   *
   * @var resource
   */
  public $context;

  /**
   * A generic resource handle.
   *
   * @var resource
   */
  public $handle = NULL;

  /**
   * Instance URI (stream).
   *
   * A stream is referenced as "scheme://target".
   *
   * @var string
   */
  protected $uri;

  /**
   * {@inheritdoc}
   */
  public static function getType() {
    return StreamWrapperInterface::NORMAL;
  }

  /**
   * Gets the path that the wrapper is responsible for.
   *
   * @return string
   *   String specifying the path.
   */
  abstract public function getDirectoryPath();

  /**
   * {@inheritdoc}
   */
  public function setUri($uri) {
    $this->uri = $uri;
  }

  /**
   * {@inheritdoc}
   */
  public function getUri() {
    return $this->uri;
  }

  /**
   * Returns the local writable target of the resource within the stream.
   *
   * This function should be used in place of calls to realpath() or similar
   * functions when attempting to determine the location of a file. While
   * functions like realpath() may return the location of a read-only file, this
   * method may return a URI or path suitable for writing that is completely
   * separate from the URI used for reading.
   *
   * @param string $uri
   *   Optional URI.
   *
   * @return string|bool
   *   Returns a string representing a location suitable for writing of a file,
   *   or FALSE if unable to write to the file such as with read-only streams.
   */
  protected function getTarget($uri = NULL) {
    if (!isset($uri)) {
      $uri = $this->uri;
    }

    [, $target] = explode('://', $uri, 2);

    // Remove erroneous leading or trailing, forward-slashes and backslashes.
    return trim($target, '\/');
  }

  /**
   * {@inheritdoc}
   */
  public function realpath() {
    return $this->getLocalPath();
  }

  /**
   * Returns the canonical absolute path of the URI, if possible.
   *
   * @param string $uri
   *   (optional) The stream wrapper URI to be converted to a canonical
   *   absolute path. This may point to a directory or another type of file.
   *
   * @return string|bool
   *   If $uri is not set, returns the canonical absolute path of the URI
   *   previously set by the
   *   Drupal\Core\StreamWrapper\StreamWrapperInterface::setUri() function.
   *   If $uri is set and valid for this class, returns its canonical absolute
   *   path, as determined by the realpath() function. If $uri is set but not
   *   valid, returns FALSE.
   */
  protected function getLocalPath($uri = NULL) {
    if (!isset($uri)) {
      $uri = $this->uri;
    }
    $path = $this->getDirectoryPath() . '/' . $this->getTarget($uri);

    // In PHPUnit tests, the base path for local streams may be a virtual
    // filesystem stream wrapper URI, in which case this local stream acts like
    // a proxy. realpath() is not supported by vfsStream, because a virtual
    // file system does not have a real filepath.
    if (str_starts_with($path, 'vfs://')) {
      return $path;
    }

    $realpath = realpath($path);
    if (!$realpath) {
      // This file does not yet exist.
      $realpath = realpath(dirname($path)) . '/' . \Drupal::service('file_system')->basename($path);
    }
    $directory = realpath($this->getDirectoryPath());
    if (!$realpath || !$directory || !str_starts_with($realpath, $directory)) {
      return FALSE;
    }
    return $realpath;
  }

  /**
   * {@inheritdoc}
   */
  public function stream_open($uri, $mode, $options, &$opened_path) {
    $this->uri = $uri;
    $path = $this->getLocalPath();
    if ($path === FALSE) {
      if ($options & STREAM_REPORT_ERRORS) {
        trigger_error('stream_open() filename cannot be empty', E_USER_WARNING);
      }
      return FALSE;
    }
    $this->handle = ($options & STREAM_REPORT_ERRORS) ? fopen($path, $mode) : @fopen($path, $mode);

    if ((bool) $this->handle && $options & STREAM_USE_PATH) {
      $opened_path = $path;
    }

    return (bool) $this->handle;
  }

  /**
   * {@inheritdoc}
   */
  public function stream_lock($operation) {
    if (in_array($operation, [LOCK_SH, LOCK_EX, LOCK_UN, LOCK_NB])) {
      return flock($this->handle, $operation);
    }

    return TRUE;
  }

  /**
   * {@inheritdoc}
   */
  public function stream_read($count) {
    return fread($this->handle, $count);
  }

  /**
   * {@inheritdoc}
   */
  public function stream_write($data) {
    return fwrite($this->handle, $data);
  }

  /**
   * {@inheritdoc}
   */
  public function stream_eof() {
    return feof($this->handle);
  }

  /**
   * {@inheritdoc}
   */
  public function stream_seek($offset, $whence = SEEK_SET) {
    // fseek() returns 0 on success and -1 on a failure.
    // stream_seek()   1 on success and  0 on a failure.
    return !fseek($this->handle, $offset, $whence);
  }

  /**
   * {@inheritdoc}
   */
  public function stream_flush() {
    return fflush($this->handle);
  }

  /**
   * {@inheritdoc}
   */
  public function stream_tell() {
    return ftell($this->handle);
  }

  /**
   * {@inheritdoc}
   */
  public function stream_stat() {
    return fstat($this->handle);
  }

  /**
   * {@inheritdoc}
   */
  public function stream_close() {
    return fclose($this->handle);
  }

  /**
   * {@inheritdoc}
   */
  public function stream_cast($cast_as) {
    return $this->handle ?: FALSE;
  }

  /**
   * {@inheritdoc}
   */
  public function stream_metadata($uri, $option, $value) {
    $target = $this->getLocalPath($uri);
    $return = FALSE;
    switch ($option) {
      case STREAM_META_TOUCH:
        if (!empty($value)) {
          $return = touch($target, $value[0], $value[1]);
        }
        else {
          $return = touch($target);
        }
        break;

      case STREAM_META_OWNER_NAME:
      case STREAM_META_OWNER:
        $return = chown($target, $value);
        break;

      case STREAM_META_GROUP_NAME:
      case STREAM_META_GROUP:
        $return = chgrp($target, $value);
        break;

      case STREAM_META_ACCESS:
        $return = chmod($target, $value);
        break;
    }
    if ($return) {
      // For convenience clear the file status cache of the underlying file,
      // since metadata operations are often followed by file status checks.
      clearstatcache(TRUE, $target);
    }
    return $return;
  }

  /**
   * {@inheritdoc}
   *
   * Since Windows systems do not allow it and it is not needed for most use
   * cases anyway, this method is not supported on local files and will trigger
   * an error and return false. If needed, custom subclasses can provide
   * OS-specific implementations for advanced use cases.
   */
  public function stream_set_option($option, $arg1, $arg2) {
    trigger_error('stream_set_option() not supported for local file based stream wrappers', E_USER_WARNING);
    return FALSE;
  }

  /**
   * {@inheritdoc}
   */
  public function stream_truncate($new_size) {
    return ftruncate($this->handle, $new_size);
  }

  /**
   * {@inheritdoc}
   */
  public function unlink($uri) {
    $this->uri = $uri;
    return $this->getFileSystem()->unlink($this->getLocalPath());
  }

  /**
   * {@inheritdoc}
   */
  public function rename($from_uri, $to_uri) {
    return rename($this->getLocalPath($from_uri), $this->getLocalPath($to_uri));
  }

  /**
   * {@inheritdoc}
   */
  public function dirname($uri = NULL) {
    [$scheme] = explode('://', $uri, 2);
    $target = $this->getTarget($uri);
    $dirname = dirname($target);

    if ($dirname == '.') {
      $dirname = '';
    }

    return $scheme . '://' . $dirname;
  }

  /**
   * {@inheritdoc}
   */
  public function mkdir($uri, $mode, $options) {
    $this->uri = $uri;
    $recursive = (bool) ($options & STREAM_MKDIR_RECURSIVE);
    if ($recursive) {
      // $this->getLocalPath() fails if $uri has multiple levels of directories
      // that do not yet exist.
      $local_path = $this->getDirectoryPath() . '/' . $this->getTarget($uri);
    }
    else {
      $local_path = $this->getLocalPath($uri);
    }
    /** @var \Drupal\Core\File\FileSystemInterface $file_system */
    $file_system = \Drupal::service('file_system');
    if ($options & STREAM_REPORT_ERRORS) {
      return $file_system->mkdir($local_path, $mode, $recursive);
    }
    else {
      return @$file_system->mkdir($local_path, $mode, $recursive);
    }
  }

  /**
   * {@inheritdoc}
   */
  public function rmdir($uri, $options) {
    $this->uri = $uri;
    /** @var \Drupal\Core\File\FileSystemInterface $file_system */
    $file_system = \Drupal::service('file_system');
    if ($options & STREAM_REPORT_ERRORS) {
      return $file_system->rmdir($this->getLocalPath());
    }
    else {
      return @$file_system->rmdir($this->getLocalPath());
    }
  }

  /**
   * {@inheritdoc}
   */
  public function url_stat($uri, $flags) {
    $this->uri = $uri;
    $path = $this->getLocalPath();
    // Suppress warnings if requested or if the file or directory does not
    // exist. This is consistent with PHP's plain filesystem stream wrapper.
    if ($flags & STREAM_URL_STAT_QUIET || !file_exists($path)) {
      return @stat($path);
    }
    else {
      return stat($path);
    }
  }

  /**
   * {@inheritdoc}
   */
  public function dir_opendir($uri, $options) {
    $this->uri = $uri;
    $this->handle = opendir($this->getLocalPath());

    return (bool) $this->handle;
  }

  /**
   * {@inheritdoc}
   */
  public function dir_readdir() {
    return readdir($this->handle);
  }

  /**
   * {@inheritdoc}
   */
  public function dir_rewinddir() {
    rewinddir($this->handle);
    // We do not really have a way to signal a failure as rewinddir() does not
    // have a return value and there is no way to read a directory handler
    // without advancing to the next file.
    return TRUE;
  }

  /**
   * {@inheritdoc}
   */
  public function dir_closedir() {
    closedir($this->handle);
    // We do not really have a way to signal a failure as closedir() does not
    // have a return value.
    return TRUE;
  }

  /**
   * Returns file system service.
   *
   * @return \Drupal\Core\File\FileSystemInterface
   *   The file system service.
   */
  private function getFileSystem() {
    return \Drupal::service('file_system');
  }

}
