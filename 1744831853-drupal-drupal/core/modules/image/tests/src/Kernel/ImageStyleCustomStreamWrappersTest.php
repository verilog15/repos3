<?php

declare(strict_types=1);

namespace Drupal\Tests\image\Kernel;

use Drupal\Core\DependencyInjection\ContainerBuilder;
use Drupal\Core\StreamWrapper\PrivateStream;
use Drupal\Core\StreamWrapper\PublicStream;
use Drupal\Core\StreamWrapper\StreamWrapperManager;
use Drupal\file_test\StreamWrapper\DummyReadOnlyStreamWrapper;
use Drupal\file_test\StreamWrapper\DummyRemoteReadOnlyStreamWrapper;
use Drupal\file_test\StreamWrapper\DummyStreamWrapper;
use Drupal\image\Entity\ImageStyle;
use Drupal\KernelTests\KernelTestBase;

/**
 * Tests derivative generation with source images using stream wrappers.
 *
 * @group image
 */
class ImageStyleCustomStreamWrappersTest extends KernelTestBase {

  /**
   * {@inheritdoc}
   */
  protected static $modules = ['system', 'image'];

  /**
   * A testing image style entity.
   *
   * @var \Drupal\image\ImageStyleInterface
   */
  protected $imageStyle;

  /**
   * The file system service.
   *
   * @var \Drupal\Core\File\FileSystemInterface
   */
  protected $fileSystem;

  /**
   * {@inheritdoc}
   */
  protected function setUp(): void {
    parent::setUp();
    $this->fileSystem = $this->container->get('file_system');
    $this->config('system.file')
      ->set('default_scheme', 'public')
      ->set('allow_insecure_uploads', FALSE)
      ->set('temporary_maximum_age', 21600)
      ->save();
    $this->imageStyle = ImageStyle::create([
      'name' => 'test',
      'label' => 'Test',
    ]);
    $this->imageStyle->save();
  }

  /**
   * {@inheritdoc}
   */
  public function register(ContainerBuilder $container): void {
    parent::register($container);
    foreach ($this->providerTestCustomStreamWrappers() as $stream_wrapper) {
      $scheme = $stream_wrapper[0];
      $class = $stream_wrapper[2];
      $container->register("stream_wrapper.$scheme", $class)
        ->addTag('stream_wrapper', ['scheme' => $scheme]);
    }
  }

  /**
   * Tests derivative creation with several source on a local writable stream.
   *
   * @param string $source_scheme
   *   The source stream wrapper scheme.
   * @param string $expected_scheme
   *   The derivative expected stream wrapper scheme.
   *
   * @dataProvider providerTestCustomStreamWrappers
   */
  public function testCustomStreamWrappers($source_scheme, $expected_scheme): void {
    $derivative_uri = $this->imageStyle->buildUri("$source_scheme://some/path/image.png");
    $derivative_scheme = StreamWrapperManager::getScheme($derivative_uri);

    // Check that the derivative scheme is the expected scheme.
    $this->assertSame($expected_scheme, $derivative_scheme);

    // Check that the derivative URI is the expected one.
    $expected_uri = "$expected_scheme://styles/{$this->imageStyle->id()}/$source_scheme/some/path/image.png";
    $this->assertSame($expected_uri, $derivative_uri);
  }

  /**
   * Provide test cases for testCustomStreamWrappers().
   *
   * Derivatives created from writable source stream wrappers will inherit the
   * scheme from source. Derivatives created from read-only stream wrappers will
   * fall-back to the default scheme.
   *
   * @return array[]
   *   An array having each element an array with three items:
   *   - The source stream wrapper scheme.
   *   - The derivative expected stream wrapper scheme.
   *   - The stream wrapper service class.
   */
  public static function providerTestCustomStreamWrappers() {
    return [
      ['public', 'public', PublicStream::class],
      ['private', 'private', PrivateStream::class],
      ['dummy', 'dummy', DummyStreamWrapper::class],
      ['dummy-readonly', 'public', DummyReadOnlyStreamWrapper::class],
      ['dummy-remote-readonly', 'public', DummyRemoteReadOnlyStreamWrapper::class],
    ];
  }

}
