import logging
from typing import Any, Callable, Coroutine, Dict, List, Mapping, Optional

from argos.controllers.progress import ProgressNotifierProtocol

LOGGER = logging.getLogger(__name__)

_CALL_SIZE = 20


async def call_by_slice(
    func: Callable[[List[str]], Coroutine[Any, Any, Optional[Dict[str, Any]]]],
    *,
    params: List[str],
    call_size: Optional[int] = None,
    notifier: Optional[ProgressNotifierProtocol] = None,
) -> Dict[str, Any]:
    """Make multiple synchronous calls.

    The argument ``params`` is split in slices of bounded
    length. There's one ``func`` call per slice.

    Args:
        func: Callable that will be called.

        params: List of parameters.

        call_size: Number of parameters to handle through each call.

        notifier: Progress notifier to call on each iteration

    Returns:
        Dictionary merging all calls return values.

    """
    call_size = call_size if call_size is not None and call_size > 0 else _CALL_SIZE
    call_count = len(params) // call_size + (0 if len(params) % call_size == 0 else 1)
    result: Dict[str, Any] = {}
    step = 0
    for i in range(call_count):
        params_slice = params[i * call_size : (i + 1) * call_size]
        ith_result = await func(params_slice)
        if notifier is not None:
            step += len(params_slice)
            notifier(step)
        if ith_result is None:
            break
        result.update(ith_result)
    return result
