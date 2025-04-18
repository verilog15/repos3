<?php

declare(strict_types=1);

namespace Drupal\entity_test\Entity;

use Drupal\Core\Entity\Attribute\ContentEntityType;
use Drupal\Core\Entity\Routing\DefaultHtmlRouteProvider;
use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\Core\Entity\ContentEntityBase;
use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Field\BaseFieldDefinition;
use Drupal\Core\Entity\EntityStorageInterface;
use Drupal\entity_test\EntityTestAccessControlHandler;
use Drupal\entity_test\EntityTestDeleteForm;
use Drupal\entity_test\EntityTestForm;
use Drupal\entity_test\EntityTestListBuilder;
use Drupal\entity_test\EntityTestViewBuilder as TestViewBuilder;
use Drupal\entity_test\EntityTestViewsData;
use Drupal\user\EntityOwnerInterface;
use Drupal\user\UserInterface;

/**
 * Defines the test entity class.
 */
#[ContentEntityType(
  id: 'entity_test',
  label: new TranslatableMarkup('Test entity'),
  persistent_cache: FALSE,
  entity_keys: [
    'id' => 'id',
    'uuid' => 'uuid',
    'bundle' => 'type',
    'label' => 'name',
    'langcode' => 'langcode',
  ],
  handlers: [
    'list_builder' => EntityTestListBuilder::class,
    'view_builder' => TestViewBuilder::class,
    'access' => EntityTestAccessControlHandler::class,
    'form' => [
      'default' => EntityTestForm::class,
      'delete' => EntityTestDeleteForm::class,
    ],
    'route_provider' => ['html' => DefaultHtmlRouteProvider::class],
    'views_data' => EntityTestViewsData::class,
  ],
  links: [
    'canonical' => '/entity_test/{entity_test}',
    'add-form' => '/entity_test/add/{type}',
    'add-page' => '/entity_test/add',
    'edit-form' => '/entity_test/manage/{entity_test}/edit',
    'delete-form' => '/entity_test/delete/entity_test/{entity_test}',
  ],
  admin_permission: 'administer entity_test content',
  base_table: 'entity_test',
  field_ui_base_route: 'entity.entity_test.admin_form',
  list_cache_contexts: [
    'entity_test_view_grants',
  ],
)]
class EntityTest extends ContentEntityBase implements EntityOwnerInterface {

  /**
   * {@inheritdoc}
   */
  public static function preCreate(EntityStorageInterface $storage, array &$values) {
    parent::preCreate($storage, $values);
    if (empty($values['type'])) {
      $values['type'] = $storage->getEntityTypeId();
    }
  }

  /**
   * {@inheritdoc}
   */
  public static function baseFieldDefinitions(EntityTypeInterface $entity_type) {
    $fields = parent::baseFieldDefinitions($entity_type);

    $fields['name'] = BaseFieldDefinition::create('string')
      ->setLabel(t('Name'))
      ->setDescription(t('The name of the test entity.'))
      ->setTranslatable(TRUE)
      ->setSetting('max_length', 64)
      ->setDisplayOptions('view', [
        'label' => 'hidden',
        'type' => 'string',
        'weight' => -5,
      ])
      ->setDisplayOptions('form', [
        'type' => 'string_textfield',
        'weight' => -5,
      ]);

    $fields['created'] = BaseFieldDefinition::create('created')
      ->setLabel(t('Authored on'))
      ->setDescription(t('Time the entity was created'))
      ->setTranslatable(TRUE);

    $fields['user_id'] = BaseFieldDefinition::create('entity_reference')
      ->setLabel(t('User ID'))
      ->setDescription(t('The ID of the associated user.'))
      ->setSetting('target_type', 'user')
      ->setSetting('handler', 'default')
      // Default EntityTest entities to have the root user as the owner, to
      // simplify testing.
      ->setDefaultValue([0 => ['target_id' => 1]])
      ->setTranslatable(TRUE)
      ->setDisplayOptions('form', [
        'type' => 'entity_reference_autocomplete',
        'weight' => -1,
        'settings' => [
          'match_operator' => 'CONTAINS',
          'size' => '60',
          'placeholder' => '',
        ],
      ]);

    return $fields + \Drupal::state()->get($entity_type->id() . '.additional_base_field_definitions', []);
  }

  /**
   * {@inheritdoc}
   */
  public function getOwner() {
    return $this->get('user_id')->entity;
  }

  /**
   * {@inheritdoc}
   */
  public function getOwnerId() {
    return $this->get('user_id')->target_id;
  }

  /**
   * {@inheritdoc}
   */
  public function setOwnerId($uid) {
    $this->set('user_id', $uid);
    return $this;
  }

  /**
   * {@inheritdoc}
   */
  public function setOwner(UserInterface $account) {
    $this->set('user_id', $account->id());
    return $this;
  }

  /**
   * Sets the name.
   *
   * @param string $name
   *   Name of the entity.
   *
   * @return $this
   */
  public function setName($name) {
    $this->set('name', $name);
    return $this;
  }

  /**
   * Returns the name.
   *
   * @return string
   *   The name of the entity.
   */
  public function getName() {
    return $this->get('name')->value;
  }

  /**
   * {@inheritdoc}
   */
  public function getEntityKey($key) {
    // Typically this protected method is used internally by entity classes and
    // exposed publicly through more specific getter methods. So that test cases
    // are able to set and access entity keys dynamically, update the visibility
    // of this method to public.
    return parent::getEntityKey($key);
  }

}
