<?php

declare(strict_types=1);

namespace Drupal\Tests\system\Kernel\Token;

use Drupal\Core\Url;
use Drupal\Component\Utility\Html;
use Drupal\Component\Utility\Xss;
use Drupal\Core\Render\BubbleableMetadata;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Session\Session;
use Symfony\Component\HttpFoundation\Session\Storage\MockArraySessionStorage;

/**
 * Tests token replacement.
 *
 * @group system
 */
class TokenReplaceKernelTest extends TokenReplaceKernelTestBase {

  /**
   * {@inheritdoc}
   */
  protected function setUp(): void {
    parent::setUp();
    // Set the site name to something other than an empty string.
    $this->config('system.site')->set('name', 'Drupal')->save();
  }

  /**
   * Tests whether token-replacement works in various contexts.
   */
  public function testSystemTokenRecognition(): void {
    // Generate prefixes and suffixes for the token context.
    $tests = [
      ['prefix' => 'this is the ', 'suffix' => ' site'],
      ['prefix' => 'this is the', 'suffix' => 'site'],
      ['prefix' => '[', 'suffix' => ']'],
      ['prefix' => '', 'suffix' => ']]]'],
      ['prefix' => '[[[', 'suffix' => ''],
      ['prefix' => ':[:', 'suffix' => '--]'],
      ['prefix' => '-[-', 'suffix' => ':]:'],
      ['prefix' => '[:', 'suffix' => ']'],
      ['prefix' => '[site:', 'suffix' => ':name]'],
      ['prefix' => '[site:', 'suffix' => ']'],
    ];

    // Check if the token is recognized in each of the contexts.
    foreach ($tests as $test) {
      $input = $test['prefix'] . '[site:name]' . $test['suffix'];
      $expected = $test['prefix'] . 'Drupal' . $test['suffix'];
      $output = $this->tokenService->replace($input, [], ['langcode' => $this->interfaceLanguage->getId()]);
      $this->assertSame($expected, $output, "Token recognized in string $input");
    }

    // Test token replacement when the string contains no tokens.
    $this->assertEquals('No tokens here.', $this->tokenService->replace('No tokens here.'));
  }

  /**
   * Tests the clear parameter.
   */
  public function testClear(): void {
    // Valid token.
    $source = '[site:name]';
    // No user passed in, should be untouched.
    $source .= '[user:name]';
    // Non-existing token.
    $source .= '[bogus:token]';

    // Replace with the clear parameter, only the valid token should remain.
    $target = Html::escape($this->config('system.site')->get('name'));
    $result = $this->tokenService->replace(
      $source,
      [],
      [
        'langcode' => $this->interfaceLanguage->getId(),
        'clear' => TRUE,
      ]);
    $this->assertEquals($target, $result, 'Valid tokens replaced while invalid tokens ignored.');

    $target .= '[user:name]';
    $target .= '[bogus:token]';
    $result = $this->tokenService->replace($source, [], ['langcode' => $this->interfaceLanguage->getId()]);
    $this->assertEquals($target, $result, 'Valid tokens replaced while invalid tokens ignored.');
  }

  /**
   * Tests the generation of all system site information tokens.
   */
  public function testSystemSiteTokenReplacement(): void {
    $url_options = [
      'absolute' => TRUE,
      'language' => $this->interfaceLanguage,
    ];

    $slogan = '<blink>Slogan</blink>';
    $safe_slogan = Xss::filterAdmin($slogan);

    // Set a few site variables.
    $config = $this->config('system.site');
    $config
      ->set('name', '<strong>Drupal<strong>')
      ->set('slogan', $slogan)
      ->set('mail', 'simpletest@example.com')
      ->save();

    // Generate and test tokens.
    $tests = [];
    $tests['[site:name]'] = Html::escape($config->get('name'));
    $tests['[site:slogan]'] = $safe_slogan;
    $tests['[site:mail]'] = $config->get('mail');
    $tests['[site:url]'] = Url::fromRoute('<front>', [], $url_options)->toString();
    $tests['[site:url-brief]'] = preg_replace(['!^https?://!', '!/$!'], '', Url::fromRoute('<front>', [], $url_options)->toString());
    $tests['[site:base-url]'] = 'http://localhost';
    $tests['[site:login-url]'] = Url::fromRoute('user.page', [], $url_options)->toString();

    $base_bubbleable_metadata = new BubbleableMetadata();

    $metadata_tests = [];
    $metadata_tests['[site:name]'] = BubbleableMetadata::createFromObject(\Drupal::config('system.site'));
    $metadata_tests['[site:slogan]'] = BubbleableMetadata::createFromObject(\Drupal::config('system.site'));
    $metadata_tests['[site:mail]'] = BubbleableMetadata::createFromObject(\Drupal::config('system.site'));
    $bubbleable_metadata = clone $base_bubbleable_metadata;
    $metadata_tests['[site:base-url]'] = $bubbleable_metadata->addCacheContexts(['url.site']);
    $metadata_tests['[site:url]'] = $bubbleable_metadata->addCacheContexts(['url.site']);
    $metadata_tests['[site:url-brief]'] = $bubbleable_metadata;
    $metadata_tests['[site:login-url]'] = $bubbleable_metadata;

    // Test to make sure that we generated something for each token.
    $this->assertNotContains(0, array_map('strlen', $tests), 'No empty tokens generated.');

    foreach ($tests as $input => $expected) {
      $bubbleable_metadata = new BubbleableMetadata();
      $output = $this->tokenService->replace($input, [], ['langcode' => $this->interfaceLanguage->getId()], $bubbleable_metadata);
      $this->assertEquals($expected, $output, "System site information token $input replaced.");
      $this->assertEquals($metadata_tests[$input], $bubbleable_metadata);
    }

    // Test [site:base-url] and [site:base-path] token with a subdirectory.
    $request_stack = \Drupal::requestStack();
    // Test request with subdirectory on homepage.
    $server = [
      'SCRIPT_NAME' => '/subdir/index.php',
      'SCRIPT_FILENAME' => $this->root . '/subdir/index.php',
      'SERVER_NAME' => 'http://localhost',
    ];
    $request = Request::create('/subdir/', 'GET', [], [], [], $server);
    $request->setSession(new Session(new MockArraySessionStorage()));
    $request->server->add($server);
    $request_stack->push($request);
    $bubbleable_metadata = new BubbleableMetadata();
    $this->container->get('router.request_context')->setCompleteBaseUrl('http://localhost/subdir');
    $this->assertEquals('http://localhost/subdir', $this->tokenService->replace('[site:base-url]', [], ['langcode' => $this->interfaceLanguage->getId()], $bubbleable_metadata));
    $this->assertEquals((new BubbleableMetadata())->addCacheContexts(['url.site']), $bubbleable_metadata);
    $bubbleable_metadata = new BubbleableMetadata();
    $this->assertEquals('/subdir', $this->tokenService->replace('[site:base-path]', [], ['langcode' => $this->interfaceLanguage->getId()], $bubbleable_metadata));
    $this->assertEquals((new BubbleableMetadata())->addCacheContexts(['url.site']), $bubbleable_metadata);
  }

  /**
   * Tests the generation of all system date tokens.
   */
  public function testSystemDateTokenReplacement(): void {
    // Set time to one hour before request.
    $date = \Drupal::time()->getRequestTime() - 3600;

    // Generate and test tokens.
    $tests = [];
    $date_formatter = \Drupal::service('date.formatter');
    $tests['[date:short]'] = $date_formatter->format($date, 'short', '', NULL, $this->interfaceLanguage->getId());
    $tests['[date:medium]'] = $date_formatter->format($date, 'medium', '', NULL, $this->interfaceLanguage->getId());
    $tests['[date:long]'] = $date_formatter->format($date, 'long', '', NULL, $this->interfaceLanguage->getId());
    $tests['[date:custom:m/j/Y]'] = $date_formatter->format($date, 'custom', 'm/j/Y', NULL, $this->interfaceLanguage->getId());
    $tests['[date:since]'] = $date_formatter->formatTimeDiffSince($date, ['langcode' => $this->interfaceLanguage->getId()]);
    $tests['[date:raw]'] = Xss::filter($date);

    // Test to make sure that we generated something for each token.
    $this->assertNotContains(0, array_map('strlen', $tests), 'No empty tokens generated.');

    foreach ($tests as $input => $expected) {
      $output = $this->tokenService->replace($input, ['date' => $date], ['langcode' => $this->interfaceLanguage->getId()]);
      $this->assertEquals($expected, $output, "Date token $input replaced.");
    }
  }

}
