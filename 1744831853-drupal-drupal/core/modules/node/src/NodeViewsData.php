<?php

namespace Drupal\node;

use Drupal\Core\Extension\ModuleExtensionList;
use Drupal\Core\Entity\EntityFieldManagerInterface;
use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Entity\Sql\SqlEntityStorageInterface;
use Drupal\Core\Extension\ModuleHandlerInterface;
use Drupal\Core\StringTranslation\PluralTranslatableMarkup;
use Drupal\Core\StringTranslation\TranslationInterface;
use Drupal\views\EntityViewsData;
use Symfony\Component\DependencyInjection\ContainerInterface;

/**
 * Provides the views data for the node entity type.
 */
class NodeViewsData extends EntityViewsData {

  /**
   * Constructs an NodeViewsData object.
   *
   * @param \Drupal\Core\Entity\EntityTypeInterface $entity_type
   *   The entity type to provide views integration for.
   * @param \Drupal\Core\Entity\Sql\SqlEntityStorageInterface $storage_controller
   *   The storage handler used for this entity type.
   * @param \Drupal\Core\Entity\EntityTypeManagerInterface $entity_type_manager
   *   The entity type manager.
   * @param \Drupal\Core\Extension\ModuleHandlerInterface $module_handler
   *   The module handler.
   * @param \Drupal\Core\StringTranslation\TranslationInterface $translation_manager
   *   The translation manager.
   * @param \Drupal\Core\Entity\EntityFieldManagerInterface $entity_field_manager
   *   The entity field manager.
   * @param \Drupal\Core\Extension\ModuleExtensionList|null $moduleExtensionList
   *   The module extension list.
   */
  public function __construct(
    EntityTypeInterface $entity_type,
    SqlEntityStorageInterface $storage_controller,
    EntityTypeManagerInterface $entity_type_manager,
    ModuleHandlerInterface $module_handler,
    TranslationInterface $translation_manager,
    EntityFieldManagerInterface $entity_field_manager,
    protected ?ModuleExtensionList $moduleExtensionList = NULL,
  ) {
    parent::__construct($entity_type, $storage_controller, $entity_type_manager, $module_handler, $translation_manager, $entity_field_manager);
    if ($this->moduleExtensionList === NULL) {
      @trigger_error('Calling ' . __METHOD__ . '() without the $moduleExtensionList argument is deprecated in drupal:11.2.0 and will be required in drupal:12.0.0. See https://www.drupal.org/node/3493129', E_USER_DEPRECATED);
      $this->moduleExtensionList = \Drupal::service('extension.list.module');
    }
  }

  /**
   * {@inheritdoc}
   */
  public static function createInstance(ContainerInterface $container, EntityTypeInterface $entity_type) {
    return new static(
      $entity_type,
      $container->get('entity_type.manager')->getStorage($entity_type->id()),
      $container->get('entity_type.manager'),
      $container->get('module_handler'),
      $container->get('string_translation'),
      $container->get('entity_field.manager'),
      $container->get('extension.list.module')
    );
  }

  /**
   * {@inheritdoc}
   */
  public function getViewsData() {
    $data = parent::getViewsData();

    $data['node_field_data']['table']['base']['weight'] = -10;
    $data['node_field_data']['table']['base']['access query tag'] = 'node_access';
    $data['node_field_data']['table']['wizard_id'] = 'node';

    $data['node_field_data']['nid']['argument'] = [
      'id' => 'node_nid',
      'name field' => 'title',
      'numeric' => TRUE,
      'validate type' => 'nid',
    ];

    $data['node_field_data']['title']['field']['default_formatter_settings'] = ['link_to_entity' => TRUE];
    $data['node_field_data']['title']['field']['link_to_node default'] = TRUE;

    $data['node_field_data']['type']['argument']['id'] = 'node_type';

    $data['node_field_data']['status']['filter']['label'] = $this->t('Published status');
    $data['node_field_data']['status']['filter']['type'] = 'yes-no';
    // Use status = 1 instead of status <> 0 in WHERE statement.
    $data['node_field_data']['status']['filter']['use_equal'] = TRUE;

    // Check for any extensions that use node grants and block the use of this
    // filter. If this filter is blocked then provide a helpful message.
    $node_access_implementations = $this->getNodeAccessImplementations();
    $node_access_implementation_count = count($node_access_implementations);
    if ($node_access_implementation_count === 0) {
      $status_extra_help_text = $this->t('Filters out unpublished content if the current user cannot view it.');
    }
    else {
      uasort($node_access_implementations, 'strnatcasecmp');
      $status_extra_help_text = new PluralTranslatableMarkup(
        $node_access_implementation_count,
        'This filter has no effect because the %module module controls access.',
        'This filter has no effect because these modules control access: %modules.',
        ['%module' => reset($node_access_implementations), '%modules' => implode(', ', $node_access_implementations)]
      );
    }

    $data['node_field_data']['status_extra'] = [
      'title' => $this->t('Published status or admin user'),
      'help' => $status_extra_help_text,
      'filter' => [
        'field' => 'status',
        'id' => 'node_status',
        'label' => $this->t('Published status or admin user'),
      ],
    ];

    $data['node_field_data']['promote']['help'] = $this->t('A boolean indicating whether the node is visible on the front page.');
    $data['node_field_data']['promote']['filter']['label'] = $this->t('Promoted to front page status');
    $data['node_field_data']['promote']['filter']['type'] = 'yes-no';

    $data['node_field_data']['sticky']['help'] = $this->t('A boolean indicating whether the node should sort to the top of content lists.');
    $data['node_field_data']['sticky']['filter']['label'] = $this->t('Sticky status');
    $data['node_field_data']['sticky']['filter']['type'] = 'yes-no';
    $data['node_field_data']['sticky']['sort']['help'] = $this->t('Whether or not the content is sticky. To list sticky content first, set this to descending.');

    $data['node']['node_bulk_form'] = [
      'title' => $this->t('Node operations bulk form'),
      'help' => $this->t('Add a form element that lets you run operations on multiple nodes.'),
      'field' => [
        'id' => 'node_bulk_form',
      ],
    ];

    // Bogus fields for aliasing purposes.
    // @todo Add similar support to any date field
    // @see https://www.drupal.org/node/2337507
    $data['node_field_data']['created_fulldate'] = [
      'title' => $this->t('Created date'),
      'help' => $this->t('Date in the form of CCYYMMDD.'),
      'argument' => [
        'field' => 'created',
        'id' => 'date_fulldate',
      ],
    ];

    $data['node_field_data']['created_year_month'] = [
      'title' => $this->t('Created year + month'),
      'help' => $this->t('Date in the form of YYYYMM.'),
      'argument' => [
        'field' => 'created',
        'id' => 'date_year_month',
      ],
    ];

    $data['node_field_data']['created_year'] = [
      'title' => $this->t('Created year'),
      'help' => $this->t('Date in the form of YYYY.'),
      'argument' => [
        'field' => 'created',
        'id' => 'date_year',
      ],
    ];

    $data['node_field_data']['created_month'] = [
      'title' => $this->t('Created month'),
      'help' => $this->t('Date in the form of MM (01 - 12).'),
      'argument' => [
        'field' => 'created',
        'id' => 'date_month',
      ],
    ];

    $data['node_field_data']['created_day'] = [
      'title' => $this->t('Created day'),
      'help' => $this->t('Date in the form of DD (01 - 31).'),
      'argument' => [
        'field' => 'created',
        'id' => 'date_day',
      ],
    ];

    $data['node_field_data']['created_week'] = [
      'title' => $this->t('Created week'),
      'help' => $this->t('Date in the form of WW (01 - 53).'),
      'argument' => [
        'field' => 'created',
        'id' => 'date_week',
      ],
    ];

    $data['node_field_data']['changed_fulldate'] = [
      'title' => $this->t('Updated date'),
      'help' => $this->t('Date in the form of CCYYMMDD.'),
      'argument' => [
        'field' => 'changed',
        'id' => 'date_fulldate',
      ],
    ];

    $data['node_field_data']['changed_year_month'] = [
      'title' => $this->t('Updated year + month'),
      'help' => $this->t('Date in the form of YYYYMM.'),
      'argument' => [
        'field' => 'changed',
        'id' => 'date_year_month',
      ],
    ];

    $data['node_field_data']['changed_year'] = [
      'title' => $this->t('Updated year'),
      'help' => $this->t('Date in the form of YYYY.'),
      'argument' => [
        'field' => 'changed',
        'id' => 'date_year',
      ],
    ];

    $data['node_field_data']['changed_month'] = [
      'title' => $this->t('Updated month'),
      'help' => $this->t('Date in the form of MM (01 - 12).'),
      'argument' => [
        'field' => 'changed',
        'id' => 'date_month',
      ],
    ];

    $data['node_field_data']['changed_day'] = [
      'title' => $this->t('Updated day'),
      'help' => $this->t('Date in the form of DD (01 - 31).'),
      'argument' => [
        'field' => 'changed',
        'id' => 'date_day',
      ],
    ];

    $data['node_field_data']['changed_week'] = [
      'title' => $this->t('Updated week'),
      'help' => $this->t('Date in the form of WW (01 - 53).'),
      'argument' => [
        'field' => 'changed',
        'id' => 'date_week',
      ],
    ];

    $data['node']['node_listing_empty'] = [
      'title' => $this->t('Empty Node Frontpage behavior'),
      'help' => $this->t('Provides a link to the node add overview page.'),
      'area' => [
        'id' => 'node_listing_empty',
      ],
    ];

    $data['node_field_data']['uid_revision']['title'] = $this->t('User has a revision');
    $data['node_field_data']['uid_revision']['help'] = $this->t('All nodes where a certain user has a revision');
    $data['node_field_data']['uid_revision']['real field'] = 'nid';
    $data['node_field_data']['uid_revision']['filter']['id'] = 'node_uid_revision';
    $data['node_field_data']['uid_revision']['argument']['id'] = 'node_uid_revision';

    $data['node_field_revision']['table']['wizard_id'] = 'node_revision';

    // Advertise this table as a possible base table.
    $data['node_field_revision']['table']['base']['help'] = $this->t('Content revision is a history of changes to content.');
    $data['node_field_revision']['table']['base']['defaults']['title'] = 'title';

    $data['node_field_revision']['nid']['argument'] = [
      'id' => 'node_nid',
      'numeric' => TRUE,
    ];
    // @todo the NID field needs different behavior on revision/non-revision
    //   tables. It would be neat if this could be encoded in the base field
    //   definition.
    $data['node_field_revision']['vid'] = [
      'argument' => [
        'id' => 'node_vid',
        'numeric' => TRUE,
      ],
    ] + $data['node_field_revision']['vid'];

    $data['node_field_revision']['langcode']['help'] = $this->t('The language the original content is in.');

    $data['node_field_revision']['table']['wizard_id'] = 'node_field_revision';

    $data['node_field_revision']['status']['filter']['label'] = $this->t('Published');
    $data['node_field_revision']['status']['filter']['type'] = 'yes-no';
    $data['node_field_revision']['status']['filter']['use_equal'] = TRUE;

    $data['node_field_revision']['promote']['help'] = $this->t('A boolean indicating whether the node is visible on the front page.');

    $data['node_field_revision']['sticky']['help'] = $this->t('A boolean indicating whether the node should sort to the top of content lists.');

    $data['node_field_revision']['langcode']['help'] = $this->t('The language of the content or translation.');

    $data['node_field_revision']['link_to_revision'] = [
      'field' => [
        'title' => $this->t('Link to revision'),
        'help' => $this->t('Provide a simple link to the revision.'),
        'id' => 'node_revision_link',
        'click sortable' => FALSE,
      ],
    ];

    $data['node_field_revision']['revert_revision'] = [
      'field' => [
        'title' => $this->t('Link to revert revision'),
        'help' => $this->t('Provide a simple link to revert to the revision.'),
        'id' => 'node_revision_link_revert',
        'click sortable' => FALSE,
      ],
    ];

    $data['node_field_revision']['delete_revision'] = [
      'field' => [
        'title' => $this->t('Link to delete revision'),
        'help' => $this->t('Provide a simple link to delete the content revision.'),
        'id' => 'node_revision_link_delete',
        'click sortable' => FALSE,
      ],
    ];

    // Define the base group of this table. Fields that don't have a group
    // defined will go into this field by default.
    $data['node_access']['table']['group'] = $this->t('Content access');

    // For other base tables, explain how we join.
    $data['node_access']['table']['join'] = [
      'node_field_data' => [
        'left_field' => 'nid',
        'field' => 'nid',
      ],
    ];
    $data['node_access']['nid'] = [
      'title' => $this->t('Access'),
      'help' => $this->t('Filter by access.'),
      'filter' => [
        'id' => 'node_access',
        'help' => $this->t('Filter for content by view access. <strong>Not necessary if you are using node as your base table.</strong>'),
      ],
    ];

    // Add search table, fields, filters, etc., but only if a page using the
    // node_search plugin is enabled.
    if (\Drupal::moduleHandler()->moduleExists('search')) {
      $enabled = FALSE;
      $search_page_repository = \Drupal::service('search.search_page_repository');
      foreach ($search_page_repository->getActiveSearchPages() as $page) {
        if ($page->getPlugin()->getPluginId() == 'node_search') {
          $enabled = TRUE;
          break;
        }
      }

      if ($enabled) {
        $data['node_search_index']['table']['group'] = $this->t('Search');

        // Automatically join to the node table (or actually, node_field_data).
        // Use a Views table alias to allow other modules to use this table too,
        // if they use the search index.
        $data['node_search_index']['table']['join'] = [
          'node_field_data' => [
            'left_field' => 'nid',
            'field' => 'sid',
            'table' => 'search_index',
            'extra' => "node_search_index.type = 'node_search' AND node_search_index.langcode = node_field_data.langcode",
          ],
        ];

        $data['node_search_total']['table']['join'] = [
          'node_search_index' => [
            'left_field' => 'word',
            'field' => 'word',
          ],
        ];

        $data['node_search_dataset']['table']['join'] = [
          'node_field_data' => [
            'left_field' => 'sid',
            'left_table' => 'node_search_index',
            'field' => 'sid',
            'table' => 'search_dataset',
            'extra' => 'node_search_index.type = node_search_dataset.type AND node_search_index.langcode = node_search_dataset.langcode',
            'type' => 'INNER',
          ],
        ];

        $data['node_search_index']['score'] = [
          'title' => $this->t('Score'),
          'help' => $this->t('The score of the search item. This will not be used if the search filter is not also present.'),
          'field' => [
            'id' => 'search_score',
            'float' => TRUE,
            'no group by' => TRUE,
          ],
          'sort' => [
            'id' => 'search_score',
            'no group by' => TRUE,
          ],
        ];

        $data['node_search_index']['keys'] = [
          'title' => $this->t('Search Keywords'),
          'help' => $this->t('The keywords to search for.'),
          'filter' => [
            'id' => 'search_keywords',
            'no group by' => TRUE,
            'search_type' => 'node_search',
          ],
          'argument' => [
            'id' => 'search',
            'no group by' => TRUE,
            'search_type' => 'node_search',
          ],
        ];

      }
    }

    return $data;
  }

  /**
   * Returns a list of modules that implements a node access hook.
   *
   * @return array<string,string>
   *   An associative array where keys are module machine names and values are
   *   the human-readable names.
   */
  private function getNodeAccessImplementations(): array {
    $implementations = [];
    if ($this->moduleHandler->hasImplementations('node_grants')) {
      $module_data = $this->moduleExtensionList->getAllInstalledInfo();
      foreach (['node_grants', 'node_grants_alter'] as $hook) {
        $this->moduleHandler->invokeAllWith(
          $hook,
          static function (callable $hook, string $module) use (&$implementations, $module_data) {
            $implementations[$module] = $module_data[$module]['name'];
          }
        );
      }
    }
    return $implementations;
  }

}
