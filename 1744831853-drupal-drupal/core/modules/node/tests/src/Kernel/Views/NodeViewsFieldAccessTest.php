<?php

declare(strict_types=1);

namespace Drupal\Tests\node\Kernel\Views;

use Drupal\language\Entity\ConfigurableLanguage;
use Drupal\node\Entity\Node;
use Drupal\node\Entity\NodeType;
use Drupal\user\Entity\User;
use Drupal\Tests\views\Kernel\Handler\FieldFieldAccessTestBase;

/**
 * Tests base field access in Views for the node entity.
 *
 * @group Node
 */
class NodeViewsFieldAccessTest extends FieldFieldAccessTestBase {

  /**
   * {@inheritdoc}
   */
  protected static $modules = ['node', 'entity_test'];

  /**
   * {@inheritdoc}
   */
  protected function setUp($import_test_views = TRUE): void {
    parent::setUp($import_test_views);

    $this->installEntitySchema('node');
    // Make the site multilingual to have a working language field handler.
    ConfigurableLanguage::create(['id' => 'es', 'title' => 'Spanish title', 'label' => 'Spanish label'])->save();
  }

  /**
   * Check access for node fields.
   */
  public function testNodeFields(): void {
    $user = User::create([
      'name' => 'test user',
    ]);
    $user->save();
    NodeType::create([
      'type' => 'article',
      'name' => 'Article',
    ])->save();
    $node = Node::create([
      'type' => 'article',
      'title' => 'Test title',
      'uid' => $user->id(),
      'status' => 1,
      'promote' => 1,
      'sticky' => 0,
      'created' => 123456,
    ]);

    $node->save();

    // @todo Expand the test coverage in https://www.drupal.org/node/2464635

    $this->assertFieldAccess('node', 'nid', $node->id());
    $this->assertFieldAccess('node', 'uuid', $node->uuid());
    $this->assertFieldAccess('node', 'vid', $node->id());
    $this->assertFieldAccess('node', 'type', $node->type->entity->label());
    $this->assertFieldAccess('node', 'langcode', $node->language()->getName());
    $this->assertFieldAccess('node', 'title', 'Test title');
    $this->assertFieldAccess('node', 'uid', $user->getAccountName());
    // @todo Don't we want to display Published / Unpublished by default,
    //   see https://www.drupal.org/node/2465623
    $this->assertFieldAccess('node', 'status', 'On');
    $this->assertFieldAccess('node', 'promote', 'On');
    $this->assertFieldAccess('node', 'sticky', 'Off');

    // phpcs:ignore Drupal.Files.LineLength
    // $this->assertFieldAccess('node', 'created', \Drupal::service('date.formatter')->format(123456));
    // $this->assertFieldAccess('node', 'changed', \Drupal::service('date.formatter')->format(\Drupal::time()->getRequestTime()));
  }

}
