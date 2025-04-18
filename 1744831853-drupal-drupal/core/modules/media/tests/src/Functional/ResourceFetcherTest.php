<?php

declare(strict_types=1);

namespace Drupal\Tests\media\Functional;

use Drupal\media\OEmbed\Resource;
use Drupal\Tests\media\Traits\OEmbedTestTrait;

// cspell:ignore dailymotion Schipulcon

/**
 * Tests the oEmbed resource fetcher service.
 *
 * @coversDefaultClass \Drupal\media\OEmbed\ResourceFetcher
 *
 * @group media
 */
class ResourceFetcherTest extends MediaFunctionalTestBase {

  use OEmbedTestTrait;

  /**
   * {@inheritdoc}
   */
  protected $defaultTheme = 'stark';

  /**
   * {@inheritdoc}
   */
  protected function setUp(): void {
    parent::setUp();
    $this->useFixtureProviders();
    $this->lockHttpClientToFixtures();
  }

  /**
   * Data provider for testFetchResource().
   *
   * @return array
   *   An array of test data.
   */
  public static function providerFetchResource() {
    return [
      'JSON resource' => [
        'video_vimeo.json',
        'Vimeo',
        'Drupal Rap Video - Schipulcon09',
      ],
      'XML resource' => [
        'video_dailymotion.xml',
        'Dailymotion',
        "#d8rules - Support the Rules module for Drupal 8",
      ],
    ];
  }

  /**
   * Tests resource fetching.
   *
   * @param string $resource_url
   *   The URL of the resource to fetch, relative to the base URL.
   * @param string $provider_name
   *   The expected name of the resource provider.
   * @param string $title
   *   The expected title of the resource.
   *
   * @covers ::fetchResource
   *
   * @dataProvider providerFetchResource
   */
  public function testFetchResource($resource_url, $provider_name, $title): void {
    /** @var \Drupal\media\OEmbed\Resource $resource */
    $resource = $this->container->get('media.oembed.resource_fetcher')
      ->fetchResource($resource_url);

    $this->assertInstanceOf(Resource::class, $resource);
    $this->assertSame($provider_name, $resource->getProvider()->getName());
    $this->assertSame($title, $resource->getTitle());
  }

}
