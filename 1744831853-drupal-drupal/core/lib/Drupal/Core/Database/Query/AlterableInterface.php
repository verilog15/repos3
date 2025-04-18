<?php

namespace Drupal\Core\Database\Query;

/**
 * Interface for a query that can be manipulated via an alter hook.
 */
interface AlterableInterface {

  /**
   * Adds a tag to a query.
   *
   * Tags are strings that identify a query. A query may have any number of
   * tags. Tags are used to mark a query so that alter hooks may decide if they
   * wish to take action. Tags should be all lower-case and contain only
   * letters, numbers, and underscore, and start with a letter. That is, they
   * should follow the same rules as PHP identifiers in general.
   *
   * @param string $tag
   *   The tag to add.
   *
   * @return $this
   *   The called object.
   */
  public function addTag($tag);

  /**
   * Determines if a given query has a given tag.
   *
   * @param string $tag
   *   The tag to check.
   *
   * @return bool
   *   TRUE if this query has been marked with this tag, FALSE otherwise.
   */
  public function hasTag($tag);

  /**
   * Determines if a given query has all specified tags.
   *
   * Each tag to check should be supplied as a separate argument.
   *
   * phpcs:ignore
   * @param string ...$tags
   *   A variable number of arguments, one for each tag to check.
   *
   * @return bool
   *   TRUE if this query has been marked with all specified tags, FALSE
   *   otherwise.
   *
   * @todo Remove PHPCS ignore and uncomment new method parameters before
   *   drupal:12.0.0. See https://www.drupal.org/project/drupal/issues/3501046.
   */
  public function hasAllTags(/* string ...$tags*/);

  /**
   * Determines if a given query has any specified tag.
   *
   * Each tag to check should be supplied as a separate argument.
   *
   * phpcs:ignore
   * @param string ...$tags
   *   A variable number of arguments, one for each tag to check.
   *
   * @return bool
   *   TRUE if this query has been marked with at least one of the specified
   *   tags, FALSE otherwise.
   *
   * @todo Remove PHPCS ignore and uncomment new method parameters before
   *   drupal:12.0.0. See https://www.drupal.org/project/drupal/issues/3501046.
   */
  public function hasAnyTag(/* string ...$tags*/);

  /**
   * Adds additional metadata to the query.
   *
   * Often, a query may need to provide additional contextual data to alter
   * hooks. Alter hooks may then use that information to decide if and how
   * to take action.
   *
   * @param string $key
   *   The unique identifier for this piece of metadata. Must be a string that
   *   follows the same rules as any other PHP identifier.
   * @param mixed $object
   *   The additional data to add to the query. May be any valid PHP variable.
   *
   * @return $this
   *   The called object.
   */
  public function addMetaData($key, $object);

  /**
   * Retrieves a given piece of metadata.
   *
   * @param string $key
   *   The unique identifier for the piece of metadata to retrieve.
   *
   * @return mixed
   *   The previously attached metadata object, or NULL if one doesn't exist.
   */
  public function getMetaData($key);

}
