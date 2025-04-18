<?php

declare(strict_types=1);

namespace Drupal\Tests\Core\Entity;

use Drupal\Core\Access\AccessResult;
use Drupal\Core\Cache\Context\CacheContextsManager;
use Drupal\Core\DependencyInjection\Container;
use Drupal\Core\Entity\EntityCreateAccessCheck;
use Drupal\Tests\UnitTestCase;
use Symfony\Component\HttpFoundation\InputBag;

/**
 * @coversDefaultClass \Drupal\Core\Entity\EntityCreateAccessCheck
 *
 * @group Access
 * @group Entity
 */
class EntityCreateAccessCheckTest extends UnitTestCase {

  /**
   * The mocked entity type manager.
   *
   * @var \Drupal\Core\Entity\EntityTypeManagerInterface|\PHPUnit\Framework\MockObject\MockObject
   */
  public $entityTypeManager;

  /**
   * {@inheritdoc}
   */
  protected function setUp(): void {
    parent::setUp();

    $cache_contexts_manager = $this->prophesize(CacheContextsManager::class);
    $cache_contexts_manager->assertValidTokens()->willReturn(TRUE);
    $cache_contexts_manager->reveal();
    $container = new Container();
    $container->set('cache_contexts_manager', $cache_contexts_manager);
    \Drupal::setContainer($container);

    $this->entityTypeManager = $this->createMock('Drupal\Core\Entity\EntityTypeManagerInterface');
  }

  /**
   * Provides test data for testAccess.
   *
   * @return array
   *   An array of test data for testAccess.
   */
  public static function providerTestAccess() {
    $no_access = FALSE;
    $access = TRUE;

    return [
      ['', 'entity_test', $no_access, $no_access],
      ['', 'entity_test', $access, $access],
      ['test_entity', 'entity_test:test_entity', $access, $access],
      ['test_entity', 'entity_test:test_entity', $no_access, $no_access],
      ['test_entity', 'entity_test:{bundle_argument}', $access, $access],
      ['test_entity', 'entity_test:{bundle_argument}', $no_access, $no_access],
      ['', 'entity_test:{bundle_argument}', $no_access, $no_access, FALSE],
      // When the bundle is not provided, access should be denied even if the
      // access control handler would allow access.
      ['', 'entity_test:{bundle_argument}', $access, $no_access, FALSE],
    ];
  }

  /**
   * Tests the method for checking access to routes.
   *
   * @dataProvider providerTestAccess
   */
  public function testAccess($entity_bundle, $requirement, $access, $expected, $expect_permission_context = TRUE): void {

    // Set up the access result objects for allowing or denying access.
    $access_result = $access ? AccessResult::allowed()->cachePerPermissions() : AccessResult::neutral()->cachePerPermissions();
    $expected_access_result = $expected ? AccessResult::allowed() : AccessResult::neutral();
    if ($expect_permission_context) {
      $expected_access_result->cachePerPermissions();
    }
    if (!$entity_bundle && !$expect_permission_context) {
      $expected_access_result->setReason("Could not find '{bundle_argument}' request argument, therefore cannot check create access.");
    }

    // Don't expect a call to the access control handler when we have a bundle
    // argument requirement but no bundle is provided.
    if ($entity_bundle || !str_contains($requirement, '{')) {
      $access_control_handler = $this->createMock('Drupal\Core\Entity\EntityAccessControlHandlerInterface');
      $access_control_handler->expects($this->once())
        ->method('createAccess')
        ->with($entity_bundle)
        ->willReturn($access_result);

      $this->entityTypeManager->expects($this->any())
        ->method('getAccessControlHandler')
        ->willReturn($access_control_handler);
    }

    $applies_check = new EntityCreateAccessCheck($this->entityTypeManager);

    $route = $this->getMockBuilder('Symfony\Component\Routing\Route')
      ->disableOriginalConstructor()
      ->getMock();
    $route->expects($this->any())
      ->method('getRequirement')
      ->with('_entity_create_access')
      ->willReturn($requirement);

    $raw_variables = new InputBag();
    if ($entity_bundle) {
      $raw_variables->set('bundle_argument', $entity_bundle);
    }

    $route_match = $this->createMock('Drupal\Core\Routing\RouteMatchInterface');
    $route_match->expects($this->any())
      ->method('getRawParameters')
      ->willReturn($raw_variables);

    $account = $this->createMock('Drupal\Core\Session\AccountInterface');
    $this->assertEquals($expected_access_result, $applies_check->access($route, $route_match, $account));
  }

}
