<?php

declare(strict_types=1);

namespace Drupal\Tests\system\Unit\Routing;

use Drupal\Core\Routing\RouteBuildEvent;
use Drupal\system\EventSubscriber\AdminRouteSubscriber;
use Drupal\Tests\UnitTestCase;
use Symfony\Component\Routing\Route;
use Symfony\Component\Routing\RouteCollection;

/**
 * @coversDefaultClass \Drupal\system\EventSubscriber\AdminRouteSubscriber
 * @group system
 */
class AdminRouteSubscriberTest extends UnitTestCase {

  /**
   * @covers ::alterRoutes
   * @covers ::isHtmlRoute
   *
   * @dataProvider providerTestAlterRoutes
   */
  public function testAlterRoutes(Route $route, $is_admin): void {
    $collection = new RouteCollection();
    $collection->add('the_route', $route);
    (new AdminRouteSubscriber())->onAlterRoutes(new RouteBuildEvent($collection));

    $this->assertSame($is_admin, $route->getOption('_admin_route'));
  }

  /**
   * Provides data to testAlterRoutes().
   */
  public static function providerTestAlterRoutes() {
    $data = [];
    $data['non-admin'] = [
      new Route('/foo'),
      NULL,
    ];
    $data['admin prefix'] = [
      new Route('/admin/foo'),
      TRUE,
    ];
    $data['admin only'] = [
      new Route('/admin'),
      TRUE,
    ];
    $data['admin in part of a word'] = [
      new Route('/administration/foo'),
      NULL,
    ];
    $data['admin in part of a word with admin_route option'] = [
      (new Route('/administration/foo'))
        ->setOption('_admin_route', TRUE),
      TRUE,
    ];
    $data['admin not at the start of the path'] = [
      new Route('/foo/admin/bar'),
      NULL,
    ];
    $data['admin in part of a word not at the start of the path'] = [
      new Route('/foo/administration/bar'),
      NULL,
    ];
    $data['admin option'] = [
      (new Route('/foo'))
        ->setOption('_admin_route', TRUE),
      TRUE,
    ];
    $data['admin prefix, non-HTML format'] = [
      (new Route('/admin/foo'))
        ->setRequirement('_format', 'json'),
      NULL,
    ];
    $data['admin option, non-HTML format'] = [
      (new Route('/foo'))
        ->setRequirement('_format', 'json')
        ->setOption('_admin_route', TRUE),
      TRUE,
    ];
    $data['admin prefix, HTML format'] = [
      (new Route('/admin/foo'))
        ->setRequirement('_format', 'html'),
      TRUE,
    ];
    $data['admin prefix, multi-format including HTML'] = [
      (new Route('/admin/foo'))
        ->setRequirement('_format', 'json|html'),
      TRUE,
    ];
    return $data;
  }

}
