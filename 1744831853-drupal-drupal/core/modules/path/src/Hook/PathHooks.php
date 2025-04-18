<?php

namespace Drupal\path\Hook;

use Drupal\Core\Language\LanguageInterface;
use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\Entity\ContentEntityInterface;
use Drupal\Core\Field\BaseFieldDefinition;
use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\path\PathAliasListBuilder;
use Drupal\Core\Entity\Routing\AdminHtmlRouteProvider;
use Drupal\Core\Entity\ContentEntityDeleteForm;
use Drupal\path\PathAliasForm;
use Drupal\Core\Url;
use Drupal\Core\Routing\RouteMatchInterface;
use Drupal\Core\Hook\Attribute\Hook;

/**
 * Hook implementations for path.
 */
class PathHooks {

  use StringTranslationTrait;

  /**
   * Implements hook_help().
   */
  #[Hook('help')]
  public function help($route_name, RouteMatchInterface $route_match): ?string {
    switch ($route_name) {
      case 'help.page.path':
        $output = '';
        $output .= '<h2>' . $this->t('About') . '</h2>';
        $output .= '<p>' . $this->t('The Path module allows you to specify an alias, or custom URL, for any existing internal system path. Aliases should not be confused with URL redirects, which allow you to forward a changed or inactive URL to a new URL. In addition to making URLs more readable, aliases also help search engines index content more effectively. Multiple aliases may be used for a single internal system path. To automate the aliasing of paths, you can install the contributed module <a href=":pathauto">Pathauto</a>. For more information, see the <a href=":path">online documentation for the Path module</a>.', [
          ':path' => 'https://www.drupal.org/documentation/modules/path',
          ':pathauto' => 'https://www.drupal.org/project/pathauto',
        ]) . '</p>';
        $output .= '<h2>' . $this->t('Uses') . '</h2>';
        $output .= '<dl>';
        $output .= '<dt>' . $this->t('Creating aliases') . '</dt>';
        $output .= '<dd>' . $this->t('If you create or edit a taxonomy term you can add an alias (for example <em>music/jazz</em>) in the field "URL alias". When creating or editing content you can add an alias (for example <em>about-us/team</em>) under the section "URL path settings" in the field "URL alias". Aliases for any other path can be added through the page <a href=":aliases">URL aliases</a>. To add aliases a user needs the permission <a href=":permissions">Create and edit URL aliases</a>.', [
          ':aliases' => Url::fromRoute('entity.path_alias.collection')->toString(),
          ':permissions' => Url::fromRoute('user.admin_permissions.module', [
            'modules' => 'path',
          ])->toString(),
        ]) . '</dd>';
        $output .= '<dt>' . $this->t('Managing aliases') . '</dt>';
        $output .= '<dd>' . $this->t('The Path module provides a way to search and view a <a href=":aliases">list of all aliases</a> that are in use on your website. Aliases can be added, edited and deleted through this list.', [
          ':aliases' => Url::fromRoute('entity.path_alias.collection')->toString(),
        ]) . '</dd>';
        $output .= '</dl>';
        return $output;

      case 'entity.path_alias.collection':
        return '<p>' . $this->t("An alias defines a different name for an existing URL path - for example, the alias 'about' for the URL path 'node/1'. A URL path can have multiple aliases.") . '</p>';

      case 'entity.path_alias.add_form':
        return '<p>' . $this->t('Enter the path you wish to create the alias for, followed by the name of the new alias.') . '</p>';
    }
    return NULL;
  }

  /**
   * Implements hook_entity_type_alter().
   */
  #[Hook('entity_type_alter')]
  public function entityTypeAlter(array &$entity_types) : void {
    // @todo Remove the conditional once core fully supports "path_alias" as an
    //   optional module. See https://drupal.org/node/3092090.
    /** @var \Drupal\Core\Entity\EntityTypeInterface[] $entity_types */
    if (isset($entity_types['path_alias'])) {
      $entity_types['path_alias']->setFormClass('default', PathAliasForm::class);
      $entity_types['path_alias']->setFormClass('delete', ContentEntityDeleteForm::class);
      $entity_types['path_alias']->setHandlerClass('route_provider', ['html' => AdminHtmlRouteProvider::class]);
      $entity_types['path_alias']->setListBuilderClass(PathAliasListBuilder::class);
      $entity_types['path_alias']->setLinkTemplate('collection', '/admin/config/search/path');
      $entity_types['path_alias']->setLinkTemplate('add-form', '/admin/config/search/path/add');
      $entity_types['path_alias']->setLinkTemplate('edit-form', '/admin/config/search/path/edit/{path_alias}');
      $entity_types['path_alias']->setLinkTemplate('delete-form', '/admin/config/search/path/delete/{path_alias}');
    }
  }

  /**
   * Implements hook_entity_base_field_info_alter().
   */
  #[Hook('entity_base_field_info_alter')]
  public function entityBaseFieldInfoAlter(&$fields, EntityTypeInterface $entity_type): void {
    /** @var \Drupal\Core\Field\BaseFieldDefinition[] $fields */
    if ($entity_type->id() === 'path_alias') {
      $fields['langcode']->setDisplayOptions('form', [
        'type' => 'language_select',
        'weight' => 0,
        'settings' => [
          'include_locked' => FALSE,
        ],
      ]);
      $fields['path']->setDisplayOptions('form', ['type' => 'string_textfield', 'weight' => 5, 'settings' => ['size' => 45]]);
      $fields['alias']->setDisplayOptions('form', ['type' => 'string_textfield', 'weight' => 10, 'settings' => ['size' => 45]]);
    }
  }

  /**
   * Implements hook_entity_base_field_info().
   */
  #[Hook('entity_base_field_info')]
  public function entityBaseFieldInfo(EntityTypeInterface $entity_type): array {
    if (in_array($entity_type->id(), ['taxonomy_term', 'node', 'media'], TRUE)) {
      $fields['path'] = BaseFieldDefinition::create('path')->setLabel($this->t('URL alias'))->setTranslatable(TRUE)->setDisplayOptions('form', ['type' => 'path', 'weight' => 30])->setDisplayConfigurable('form', TRUE)->setComputed(TRUE);
      return $fields;
    }
    return [];
  }

  /**
   * Implements hook_entity_translation_create().
   */
  #[Hook('entity_translation_create')]
  public function entityTranslationCreate(ContentEntityInterface $translation): void {
    foreach ($translation->getFieldDefinitions() as $field_name => $field_definition) {
      if ($field_definition->getType() === 'path' && $translation->get($field_name)->pid) {
        // If there are values and a path ID, update the langcode and unset the
        // path ID to save this as a new alias.
        $translation->get($field_name)->langcode = $translation->language()->getId();
        $translation->get($field_name)->pid = NULL;
      }
    }
  }

  /**
   * Implements hook_field_widget_single_element_form_alter().
   */
  #[Hook('field_widget_single_element_form_alter')]
  public function fieldWidgetSingleElementFormAlter(&$element, FormStateInterface $form_state, $context): void {
    $field_definition = $context['items']->getFieldDefinition();
    $field_name = $field_definition->getName();
    $entity_type = $field_definition->getTargetEntityTypeId();
    $widget_name = $context['widget']->getPluginId();
    if ($entity_type === 'path_alias') {
      if (($field_name === 'path' || $field_name === 'alias') && $widget_name === 'string_textfield') {
        $element['value']['#field_prefix'] = \Drupal::service('router.request_context')->getCompleteBaseUrl();
      }
      if ($field_name === 'langcode') {
        $element['value']['#description'] = $this->t('A path alias set for a specific language will always be used when displaying this page in that language, and takes precedence over path aliases set as <em>- Not specified -</em>.');
        $element['value']['#empty_value'] = LanguageInterface::LANGCODE_NOT_SPECIFIED;
        $element['value']['#empty_option'] = $this->t('- Not specified -');
      }
      if ($field_name === 'path') {
        $element['value']['#description'] = $this->t('Specify the existing path you wish to alias. For example: /node/28, /media/1, /taxonomy/term/1.');
      }
      if ($field_name === 'alias') {
        $element['value']['#description'] = $this->t('Specify an alternative path by which this data can be accessed. For example, type "/about" when writing an about page.');
      }
    }
  }

}
