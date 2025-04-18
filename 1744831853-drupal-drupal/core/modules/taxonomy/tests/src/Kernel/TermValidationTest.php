<?php

declare(strict_types=1);

namespace Drupal\Tests\taxonomy\Kernel;

use Drupal\KernelTests\Core\Entity\EntityKernelTestBase;

/**
 * Tests term validation constraints.
 *
 * @group taxonomy
 */
class TermValidationTest extends EntityKernelTestBase {

  /**
   * {@inheritdoc}
   */
  protected static $modules = ['taxonomy'];

  /**
   * {@inheritdoc}
   */
  protected function setUp(): void {
    parent::setUp();
    $this->installEntitySchema('taxonomy_term');
  }

  /**
   * Tests the term validation constraints.
   */
  public function testValidation(): void {
    $this->entityTypeManager->getStorage('taxonomy_vocabulary')->create([
      'vid' => 'tags',
      'name' => 'Tags',
    ])->save();
    $term = $this->entityTypeManager->getStorage('taxonomy_term')->create([
      'name' => 'test',
      'vid' => 'tags',
    ]);
    $violations = $term->validate();
    $this->assertCount(0, $violations, 'No violations when validating a default term.');

    $term->set('name', $this->randomString(256));
    $violations = $term->validate();
    $this->assertCount(1, $violations, 'Violation found when name is too long.');
    $this->assertEquals('name.0.value', $violations[0]->getPropertyPath());
    $field_label = $term->get('name')->getFieldDefinition()->getLabel();
    $this->assertEquals(sprintf('%s: may not be longer than 255 characters.', $field_label), $violations[0]->getMessage());

    $term->set('name', NULL);
    $violations = $term->validate();
    $this->assertCount(1, $violations, 'Violation found when name is NULL.');
    $this->assertEquals('name', $violations[0]->getPropertyPath());
    $this->assertEquals('This value should not be null.', $violations[0]->getMessage());
    $term->set('name', 'test');

    $term->set('parent', 9999);
    $violations = $term->validate();
    $this->assertCount(1, $violations, 'Violation found when term parent is invalid.');
    $this->assertEquals('The referenced entity (taxonomy_term: 9999) does not exist.', $violations[0]->getMessage());

    $term->set('parent', 0);
    $violations = $term->validate();
    $this->assertCount(0, $violations, 'No violations for parent id 0.');
  }

}
