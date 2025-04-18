/*
 * Copyright (C) 2017-2025 Lightbend Inc. <https://www.lightbend.com>
 */

package akka.actor.typed.scaladsl

import scala.concurrent.{ ExecutionContextExecutor, Future }
import scala.concurrent.duration.FiniteDuration
import scala.reflect.ClassTag
import scala.util.Try

import org.slf4j.Logger

import akka.actor.ClassicActorContextProvider
import akka.actor.typed._
import akka.annotation.DoNotInherit
import akka.annotation.InternalApi
import akka.pattern.StatusReply
import akka.util.Timeout

/**
 * An Actor is given by the combination of a [[Behavior]] and a context in
 * which this behavior is executed. As per the Actor Model an Actor can perform
 * the following actions when processing a message:
 *
 *  - send a finite number of messages to other Actors it knows
 *  - create a finite number of Actors
 *  - designate the behavior for the next message
 *
 * In Akka the first capability is accessed by using the `!` or `tell` method
 * on an [[ActorRef]], the second is provided by [[ActorContext#spawn]]
 * and the third is implicit in the signature of [[Behavior]] in that the next
 * behavior is always returned from the message processing logic.
 *
 * An `ActorContext` in addition provides access to the Actor’s own identity (“`self`”),
 * the [[ActorSystem]] it is part of, methods for querying the list of child Actors it
 * created, access to [[Terminated]] and timed message scheduling.
 *
 * Not for user extension.
 */
@DoNotInherit
trait ActorContext[T] extends TypedActorContext[T] with ClassicActorContextProvider {

  /**
   * Get the `javadsl` of this `ActorContext`.
   *
   * This method is thread-safe and can be called from other threads than the ordinary
   * actor message processing thread, such as [[scala.concurrent.Future]] callbacks.
   */
  def asJava: akka.actor.typed.javadsl.ActorContext[T]

  /**
   * The identity of this Actor, bound to the lifecycle of this Actor instance.
   * An Actor with the same name that lives before or after this instance will
   * have a different [[ActorRef]].
   *
   * This field is thread-safe and can be called from other threads than the ordinary
   * actor message processing thread, such as [[scala.concurrent.Future]] callbacks.
   */
  def self: ActorRef[T]

  /**
   * The [[ActorSystem]] to which this Actor belongs.
   *
   * This field is thread-safe and can be called from other threads than the ordinary
   * actor message processing thread, such as [[scala.concurrent.Future]] callbacks.
   */
  implicit def system: ActorSystem[Nothing]

  /**
   * An actor specific logger.
   *
   * The logger name will be an estimated source class for the actor which is calculated when the
   * logger is first used (the logger is lazily created upon first use). If this yields the wrong
   * class or another class is preferred this can be changed with `setLoggerName`.
   *
   * *Warning*: This method is not thread-safe and must not be accessed from threads other
   * than the ordinary actor message processing thread, such as [[scala.concurrent.Future]] callbacks.
   */
  def log: Logger

  /**
   * Replace the current logger (or initialize a new logger if the logger was not touched before) with one that
   * has the given name as logger name. Logger source MDC entry "akkaSource" will be the actor path.
   *
   * *Warning*: This method is not thread-safe and must not be accessed from threads other
   * than the ordinary actor message processing thread, such as [[java.util.concurrent.CompletionStage]] callbacks.
   */
  def setLoggerName(name: String): Unit

  /**
   * Replace the current logger (or initialize a new logger if the logger was not touched before) with one that
   * has the given class name as logger name. Logger source MDC entry "akkaSource" will be the actor path.
   *
   * *Warning*: This method is not thread-safe and must not be accessed from threads other
   * than the ordinary actor message processing thread, such as [[scala.concurrent.Future]] callbacks.
   */
  def setLoggerName(clazz: Class[_]): Unit

  /**
   * The list of child Actors created by this Actor during its lifetime that
   * are still alive, in no particular order.
   *
   * *Warning*: This method is not thread-safe and must not be accessed from threads other
   * than the ordinary actor message processing thread, such as [[scala.concurrent.Future]] callbacks.
   */
  def children: Iterable[ActorRef[Nothing]]

  /**
   * The named child Actor if it is alive.
   *
   * *Warning*: This method is not thread-safe and must not be accessed from threads other
   * than the ordinary actor message processing thread, such as [[scala.concurrent.Future]] callbacks.
   */
  def child(name: String): Option[ActorRef[Nothing]]

  /**
   * Create a child Actor from the given [[akka.actor.typed.Behavior]] under a randomly chosen name.
   * It is good practice to name Actors wherever practical.
   *
   * *Warning*: This method is not thread-safe and must not be accessed from threads other
   * than the ordinary actor message processing thread, such as [[scala.concurrent.Future]] callbacks.
   */
  def spawnAnonymous[U](behavior: Behavior[U], props: Props = Props.empty): ActorRef[U]

  /**
   * Create a child Actor from the given [[akka.actor.typed.Behavior]] and with the given name.
   *
   * *Warning*: This method is not thread-safe and must not be accessed from threads other
   * than the ordinary actor message processing thread, such as [[scala.concurrent.Future]] callbacks.
   */
  def spawn[U](behavior: Behavior[U], name: String, props: Props = Props.empty): ActorRef[U]

  /**
   * Delegate message and signal's execution by given [[akka.actor.typed.Behavior]]
   * using [[Behavior.interpretMessage]] or [[Behavior.interpretSignal]]
   *
   * note: if given [[akka.actor.typed.Behavior]] resulting [[Behaviors.same]] that will cause context switching to the given behavior
   * and if result is [[Behaviors.unhandled]] that will trigger the [[akka.actor.typed.scaladsl.ActorContext.onUnhandled]]
   * then switching to the given behavior.
   */
  def delegate(delegator: Behavior[T], msg: T): Behavior[T]

  /**
   * Force the child Actor under the given name to terminate after it finishes
   * processing its current message. Nothing happens if the ActorRef is a child that is already stopped.
   *
   * *Warning*: This method is not thread-safe and must not be accessed from threads other
   * than the ordinary actor message processing thread, such as [[scala.concurrent.Future]] callbacks.
   *
   *  @throws IllegalArgumentException if the given actor ref is not a direct child of this actor
   */
  def stop[U](child: ActorRef[U]): Unit

  /**
   * Register for [[akka.actor.typed.Terminated]] notification once the Actor identified by the
   * given [[ActorRef]] terminates. This message is also sent when the watched actor
   * is on a node that has been removed from the cluster when using Akka Cluster.
   *
   * `watch` is idempotent if it is not mixed with `watchWith`.
   *
   * It will fail with an [[IllegalStateException]] if the same subject was watched before using `watchWith`.
   * To clear the termination message, unwatch first.
   *
   * *Warning*: This method is not thread-safe and must not be accessed from threads other
   * than the ordinary actor message processing thread, such as [[scala.concurrent.Future]] callbacks.
   */
  def watch[U](other: ActorRef[U]): Unit

  /**
   * Register for termination notification with a custom message once the Actor identified by the
   * given [[ActorRef]] terminates. This message is also sent when the watched actor
   * is on a node that has been removed from the cluster when using using Akka Cluster.
   *
   * `watchWith` is idempotent if it is called with the same `msg` and not mixed with `watch`.
   *
   * It will fail with an [[IllegalStateException]] if the same subject was watched before using `watch` or `watchWith` with
   * another termination message. To change the termination message, unwatch first.
   *
   * *Warning*: This method is not thread-safe and must not be accessed from threads other
   * than the ordinary actor message processing thread, such as [[scala.concurrent.Future]] callbacks.
   */
  def watchWith[U](other: ActorRef[U], msg: T): Unit

  /**
   * Revoke the registration established by `watch`. A [[Terminated]]
   * notification will not subsequently be received for the referenced Actor.
   *
   * *Warning*: This method is not thread-safe and must not be accessed from threads other
   * than the ordinary actor message processing thread, such as [[scala.concurrent.Future]] callbacks.
   */
  def unwatch[U](other: ActorRef[U]): Unit

  /**
   * Schedule the sending of a notification in case no other
   * message is received during the given period of time. The timeout starts anew
   * with each received message. Use `cancelReceiveTimeout` to switch off this
   * mechanism.
   *
   * *Warning*: This method is not thread-safe and must not be accessed from threads other
   * than the ordinary actor message processing thread, such as [[scala.concurrent.Future]] callbacks.
   */
  def setReceiveTimeout(timeout: FiniteDuration, msg: T): Unit

  /**
   * Cancel the sending of receive timeout notifications.
   *
   * *Warning*: This method is not thread-safe and must not be accessed from threads other
   * than the ordinary actor message processing thread, such as [[scala.concurrent.Future]] callbacks.
   */
  def cancelReceiveTimeout(): Unit

  /**
   * Schedule the sending of the given message to the given target Actor after
   * the given time period has elapsed. The scheduled action can be cancelled
   * by invoking [[akka.actor.Cancellable#cancel]] on the returned
   * handle.
   *
   * This method is thread-safe and can be called from other threads than the ordinary
   * actor message processing thread, such as [[scala.concurrent.Future]] callbacks.
   */
  def scheduleOnce[U](delay: FiniteDuration, target: ActorRef[U], msg: U): akka.actor.Cancellable

  /**
   * This Actor’s execution context. It can be used to run asynchronous tasks
   * like [[scala.concurrent.Future]] operators.
   *
   * This field is thread-safe and can be called from other threads than the ordinary
   * actor message processing thread, such as [[scala.concurrent.Future]] callbacks.
   */
  implicit def executionContext: ExecutionContextExecutor

  /**
   * INTERNAL API: It is currently internal because it's too easy to create
   * resource leaks by spawning adapters without stopping them. `messageAdapter`
   * is the public API.
   *
   * Create a "lightweight" child actor that will convert or wrap messages such that
   * other Actor’s protocols can be ingested by this Actor. You are strongly advised
   * to cache these ActorRefs or to stop them when no longer needed.
   *
   * The name of the child actor will be composed of a unique identifier
   * starting with a dollar sign to which the given `name` argument is
   * appended, with an inserted hyphen between these two parts. Therefore
   * the given `name` argument does not need to be unique within the scope
   * of the parent actor.
   *
   * The function is applied inside the "parent" actor and can safely access
   * state of the "parent".
   */
  @InternalApi private[akka] def spawnMessageAdapter[U](f: U => T, name: String): ActorRef[U]

  /**
   * INTERNAL API: See `spawnMessageAdapter` with name parameter
   */
  @InternalApi private[akka] def spawnMessageAdapter[U](f: U => T): ActorRef[U]

  /**
   * Create a message adapter that will convert or wrap messages such that other Actor’s
   * protocols can be ingested by this Actor.
   *
   * You can register several message adapters for different message classes.
   * It's only possible to have one message adapter per message class to make sure
   * that the number of adapters are not growing unbounded if registered repeatedly.
   * That also means that a registered adapter will replace an existing adapter for
   * the same message class.
   *
   * A message adapter will be used if the message class matches the given class or
   * is a subclass thereof. The registered adapters are tried in reverse order of
   * their registration order, i.e. the last registered first.
   *
   * A message adapter (and the returned `ActorRef`) has the same lifecycle as
   * this actor. It's recommended to register the adapters in a top level
   * `Behaviors.setup` or constructor of `AbstractBehavior` but it's possible to
   * register them later also if needed. Message adapters don't have to be stopped since
   * they consume no resources other than an entry in an internal `Map` and the number
   * of adapters are bounded since it's only possible to have one per message class.
   * *
   * The function is running in this actor and can safely access state of it.
   *
   * *Warning*: This method is not thread-safe and must not be accessed from threads other
   * than the ordinary actor message processing thread, such as [[scala.concurrent.Future]] callbacks.
   */
  def messageAdapter[U: ClassTag](f: U => T): ActorRef[U]

  /**
   * Perform a single request-response message interaction with another actor, and transform the messages back to
   * the protocol of this actor.
   *
   * The interaction has a timeout (to avoid a resource leak). If the timeout hits without any response it
   * will be passed as a `Failure(`[[java.util.concurrent.TimeoutException]]`)` to the `mapResponse` function
   * (this is the only "normal" way a `Failure` is passed to the function).
   *
   * For other messaging patterns with other actors, see [[ActorContext#messageAdapter]].
   *
   * This method is thread-safe and can be called from other threads than the ordinary
   * actor message processing thread, such as [[scala.concurrent.Future]] callbacks.
   *
   * @param createRequest A function that creates a message for the other actor, containing the provided `ActorRef[Res]` that
   *                      the other actor can send a message back through.
   * @param mapResponse Transforms the response from the `target` into a message this actor understands.
   *                              Should be a pure function but is executed inside the actor when the response arrives
   *                              so can safely touch the actor internals. If this function throws an exception it is
   *                              just as if the normal message receiving logic would throw.
   *
   * @tparam Req The request protocol, what the other actor accepts
   * @tparam Res The response protocol, what the other actor sends back
   */
  def ask[Req, Res](target: RecipientRef[Req], createRequest: ActorRef[Res] => Req)(
      mapResponse: Try[Res] => T)(implicit responseTimeout: Timeout, classTag: ClassTag[Res]): Unit

  /**
   * The same as [[ask]] but only for requests that result in a response of type [[akka.pattern.StatusReply]].
   * If the response is a [[akka.pattern.StatusReply.Success]] the returned future is completed successfully with the wrapped response.
   * If the status response is a [[akka.pattern.StatusReply.Error]] the returned future will be failed with the
   * exception in the error (normally a [[akka.pattern.StatusReply.ErrorMessage]]).
   */
  def askWithStatus[Req, Res](target: RecipientRef[Req], createRequest: ActorRef[StatusReply[Res]] => Req)(
      mapResponse: Try[Res] => T)(implicit responseTimeout: Timeout, classTag: ClassTag[Res]): Unit

  /**
   * Sends the result of the given `Future` to this Actor (“`self`”), after adapted it with
   * the given function.
   *
   * This method is thread-safe and can be called from other threads than the ordinary
   * actor message processing thread, such as [[scala.concurrent.Future]] callbacks.
   */
  def pipeToSelf[Value](future: Future[Value])(mapResult: Try[Value] => T): Unit

  /**
   * INTERNAL API
   */
  @InternalApi
  private[akka] def onUnhandled(msg: T): Unit

  /**
   * INTERNAL API
   */
  @InternalApi
  private[akka] def currentBehavior: Behavior[T]

  /**
   * INTERNAL API
   */
  @InternalApi
  private[akka] def hasTimer: Boolean

  /**
   * INTERNAL API
   */
  @InternalApi
  private[akka] def cancelAllTimers(): Unit

  /**
   * INTERNAL API
   */
  @InternalApi
  private[akka] def clearMdc(): Unit

  /**
   * INTERNAL API
   */
  @InternalApi private[akka] def setCurrentActorThread(): Unit

  /**
   * INTERNAL API
   */
  @InternalApi private[akka] def clearCurrentActorThread(): Unit

  /**
   * INTERNAL API
   */
  @InternalApi private[akka] def checkCurrentActorThread(): Unit

}
