<?php

declare(strict_types=1);

namespace Drupal\Tests\Core\File;

use Drupal\Core\File\Event\FileUploadSanitizeNameEvent;
use Drupal\Tests\UnitTestCase;

// cspell:ignore äöüåøhello

/**
 * FileUploadSanitizeNameEvent tests.
 *
 * @group file
 * @coversDefaultClass \Drupal\Core\File\Event\FileUploadSanitizeNameEvent
 */
class FileUploadSanitizeNameEventTest extends UnitTestCase {

  /**
   * @covers ::setFilename
   * @covers ::getFilename
   */
  public function testSetFilename(): void {
    $event = new FileUploadSanitizeNameEvent('foo.txt', '');
    $this->assertSame('foo.txt', $event->getFilename());
    $event->setFilename('foo.html');
    $this->assertSame('foo.html', $event->getFilename());
  }

  /**
   * @covers ::setFilename
   */
  public function testSetFilenameException(): void {
    $event = new FileUploadSanitizeNameEvent('foo.txt', '');
    $this->assertSame('foo.txt', $event->getFilename());
    $this->expectException(\InvalidArgumentException::class);
    $this->expectExceptionMessage('$filename must be a filename with no path information, "bar/foo.html" provided');
    $event->setFilename('bar/foo.html');
  }

  /**
   * @covers ::__construct
   * @covers ::setFilename
   */
  public function testConstructorException(): void {
    $this->expectException(\InvalidArgumentException::class);
    $this->expectExceptionMessage('$filename must be a filename with no path information, "bar/foo.txt" provided');
    new FileUploadSanitizeNameEvent('bar/foo.txt', '');
  }

  /**
   * @covers ::getAllowedExtensions
   */
  public function testAllowedExtensions(): void {
    $event = new FileUploadSanitizeNameEvent('foo.txt', '');
    $this->assertSame([], $event->getAllowedExtensions());

    $event = new FileUploadSanitizeNameEvent('foo.txt', 'gif png');
    $this->assertSame(['gif', 'png'], $event->getAllowedExtensions());
  }

  /**
   * Test event construction.
   *
   * @param string $filename
   *   The filename to test.
   *
   * @dataProvider provideFilenames
   * @covers ::__construct
   * @covers ::getFilename
   */
  public function testEventFilenameFunctions(string $filename): void {
    $event = new FileUploadSanitizeNameEvent($filename, '');
    $this->assertSame($filename, $event->getFilename());
  }

  /**
   * Provides data for testEventFilenameFunctions().
   *
   * @return array
   *   Arrays with original file name.
   */
  public static function provideFilenames() {
    return [
      'ASCII filename with extension' => [
        'example.txt',
      ],
      'ASCII filename with complex extension' => [
        'example.html.twig',
      ],
      'ASCII filename with lots of dots' => [
        'dotty.....txt',
      ],
      'Unicode filename with extension' => [
        'Ä Ö Ü Å Ø äöüåøhello.txt',
      ],
      'Unicode filename without extension' => [
        'Ä Ö Ü Å Ø äöüåøhello',
      ],
    ];
  }

  /**
   * @covers ::stopPropagation
   */
  public function testStopPropagation(): void {
    $this->expectException(\RuntimeException::class);
    $event = new FileUploadSanitizeNameEvent('test.txt', '');
    $event->stopPropagation();
  }

}
