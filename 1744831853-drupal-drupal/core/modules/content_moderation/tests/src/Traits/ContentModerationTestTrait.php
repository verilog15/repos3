<?php

declare(strict_types=1);

namespace Drupal\Tests\content_moderation\Traits;

use Drupal\content_moderation\Plugin\WorkflowType\ContentModerationInterface;
use Drupal\workflows\Entity\Workflow;
use Drupal\workflows\WorkflowInterface;

/**
 * Provides functionality for testing content moderation.
 */
trait ContentModerationTestTrait {

  /**
   * Creates the editorial workflow.
   *
   * @return \Drupal\workflows\Entity\Workflow
   *   The editorial workflow entity.
   */
  protected function createEditorialWorkflow() {
    // Allow this method to be called twice from the same test method.
    if ($workflow = Workflow::load('editorial')) {
      return $workflow;
    }
    $workflow = Workflow::create([
      'type' => 'content_moderation',
      'id' => 'editorial',
      'label' => 'Editorial',
      'type_settings' => [
        'states' => [
          'archived' => [
            'label' => 'Archived',
            'weight' => 5,
            'published' => FALSE,
            'default_revision' => TRUE,
          ],
          'draft' => [
            'label' => 'Draft',
            'published' => FALSE,
            'default_revision' => FALSE,
            'weight' => -5,
          ],
          'published' => [
            'label' => 'Published',
            'published' => TRUE,
            'default_revision' => TRUE,
            'weight' => 0,
          ],
        ],
        'transitions' => [
          'archive' => [
            'label' => 'Archive',
            'from' => ['published'],
            'to' => 'archived',
            'weight' => 2,
          ],
          'archived_draft' => [
            'label' => 'Restore to Draft',
            'from' => ['archived'],
            'to' => 'draft',
            'weight' => 3,
          ],
          'archived_published' => [
            'label' => 'Restore',
            'from' => ['archived'],
            'to' => 'published',
            'weight' => 4,
          ],
          'create_new_draft' => [
            'label' => 'Create New Draft',
            'to' => 'draft',
            'weight' => 0,
            'from' => [
              'draft',
              'published',
            ],
          ],
          'publish' => [
            'label' => 'Publish',
            'to' => 'published',
            'weight' => 1,
            'from' => [
              'draft',
              'published',
            ],
          ],
        ],
      ],
    ]);
    $workflow->save();
    return $workflow;
  }

  /**
   * Adds an entity type ID / bundle ID to the given workflow.
   *
   * @param \Drupal\workflows\WorkflowInterface $workflow
   *   A workflow object.
   * @param string $entity_type_id
   *   The entity type ID to add.
   * @param string $bundle
   *   The bundle ID to add.
   */
  protected function addEntityTypeAndBundleToWorkflow(WorkflowInterface $workflow, $entity_type_id, $bundle) {
    $moderation = $workflow->getTypePlugin();
    if ($moderation instanceof ContentModerationInterface) {
      $moderation->addEntityTypeAndBundle($entity_type_id, $bundle);
      $workflow->save();
    }
  }

}
