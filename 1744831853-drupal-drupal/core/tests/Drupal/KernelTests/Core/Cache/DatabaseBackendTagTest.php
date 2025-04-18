<?php

declare(strict_types=1);

namespace Drupal\KernelTests\Core\Cache;

use Drupal\Core\Cache\Cache;
use Drupal\Core\Database\Database;
use Drupal\Core\DependencyInjection\ContainerBuilder;
use Drupal\KernelTests\KernelTestBase;
use Symfony\Component\DependencyInjection\Reference;

/**
 * Tests DatabaseBackend cache tag implementation.
 *
 * @group Cache
 */
class DatabaseBackendTagTest extends KernelTestBase {

  /**
   * {@inheritdoc}
   */
  protected static $modules = ['system'];

  /**
   * {@inheritdoc}
   */
  public function register(ContainerBuilder $container): void {
    parent::register($container);
    // Change container to database cache backends.
    $container
      ->register('cache_factory', 'Drupal\Core\Cache\CacheFactory')
      ->addArgument(new Reference('settings'))
      ->addMethodCall('setContainer', [new Reference('service_container')]);
  }

  /**
   * Test tag invalidation.
   */
  public function testTagInvalidations(): void {
    // Create cache entry in multiple bins.
    $tags = ['test_tag:1', 'test_tag:2', 'test_tag:3'];
    $bins = ['data', 'bootstrap', 'render'];
    foreach ($bins as $bin) {
      $bin = \Drupal::cache($bin);
      $bin->set('test', 'value', Cache::PERMANENT, $tags);
      $this->assertNotEmpty($bin->get('test'), 'Cache item was set in bin.');
    }

    $connection = Database::getConnection();
    $invalidations_before = intval($connection->select('cachetags')->fields('cachetags', ['invalidations'])->condition('tag', 'test_tag:2')->execute()->fetchField());
    Cache::invalidateTags(['test_tag:2']);

    // Test that cache entry has been invalidated in multiple bins.
    foreach ($bins as $bin) {
      $bin = \Drupal::cache($bin);
      $this->assertFalse($bin->get('test'), 'Tag invalidation affected item in bin.');
    }

    // Test that only one tag invalidation has occurred.
    $invalidations_after = intval($connection->select('cachetags')->fields('cachetags', ['invalidations'])->condition('tag', 'test_tag:2')->execute()->fetchField());
    $this->assertEquals($invalidations_before + 1, $invalidations_after, 'Only one addition cache tag invalidation has occurred after invalidating a tag used in multiple bins.');
  }

}
