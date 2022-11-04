import itertools
from queue import Queue
from typing import MutableSet


class OrderedSet(MutableSet):
    """A set that preserves insertion order by internally using a dict.
    >>> OrderedSet([1, 2, "foo"])
    """

    __slots__ = ("_d",)

    def __init__(self, iterable=None):
        self._d = dict.fromkeys(iterable) if iterable else {}

    def add(self, x):
        self._d[x] = None

    def clear(self):
        self._d.clear()

    def discard(self, x):
        self._d.pop(x, None)

    def __getitem__(self, index):
        try:
            return next(itertools.islice(self._d, index, index + 1))
        except StopIteration:
            raise IndexError(f"index {index} out of range")

    def __contains__(self, x):
        return self._d.__contains__(x)

    def __len__(self):
        return self._d.__len__()

    def __iter__(self):
        return self._d.__iter__()

    def __str__(self):
        return f"{{{', '.join(str(i) for i in self)}}}"

    def __repr__(self):
        return f"<OrderedSet {self}>"


class SetQueue(Queue):
    """
    Queue with unique items
    """

    def _init(self, maxsize):
        self.queue = OrderedSet()
        self.items = dict()
        self.current = None

    def _put(self, item):
        if self.current != item.id:
            self.queue.add(item.id)
            self.items[item.id] = item

    def _get(self):
        self.current = self.queue.pop()
        item = self.items.pop(self.current)
        return item

    def clear(self):
        """
        Clears all items from the queue.
        """
        with self.mutex:
            unfinished = self.unfinished_tasks - len(self.queue)
            if unfinished <= 0:
                if unfinished < 0:
                    raise ValueError("task_done() called too many times")
                self.all_tasks_done.notify_all()
            self.unfinished_tasks = unfinished
            self._init(None)
            self.not_full.notify_all()
