from model import Tray


def test_pids_in_visible_trays_are_visible():
    tray = Tray(num_pids=9, num_trays=3)
    tray.move_pids_to_tray([0, 1, 2], 0)
    tray.move_pids_to_tray([3, 4, 5], 1)
    tray.move_pids_to_tray([6, 7, 8], 2)

    tray.visible_trays = {0}
    assert tray.is_visible(0)
    assert tray.is_visible(1)
    assert tray.is_visible(2)
    assert not tray.is_visible(3)
    assert not tray.is_visible(4)
    assert not tray.is_visible(5)
    assert not tray.is_visible(6)
    assert not tray.is_visible(7)
    assert not tray.is_visible(8)

    tray.visible_trays = {1}
    assert not tray.is_visible(0)
    assert not tray.is_visible(1)
    assert not tray.is_visible(2)
    assert tray.is_visible(3)
    assert tray.is_visible(4)
    assert tray.is_visible(5)
    assert not tray.is_visible(6)
    assert not tray.is_visible(7)
    assert not tray.is_visible(8)


def test_filter_visible_returns_only_visible_pids():
    tray = Tray(num_pids=9, num_trays=3)
    tray.move_pids_to_tray([0, 1, 2], 0)
    tray.move_pids_to_tray([3, 4, 5], 1)
    tray.move_pids_to_tray([6, 7, 8], 2)
    tray.visible_trays = {1, 2}

    assert list(tray.filter_visible(range(10))) == [3, 4, 5, 6, 7, 8]


def test_filter_visible_returns_nothing_when_there_are_no_visible_pids():
    # TODO: refactor this cause I don't really understand it!
    tray = Tray(num_pids=3, num_trays=3)
    tray.trays[0] = {1, 2, 3}
    tray.trays[1] = {4, 5, 6}
    tray.trays[2] = {7, 8, 9}
    tray.visible_trays = {1, 2}

    assert list(tray.filter_visible([1, 10])) == []


def test_tray_zero_is_default():
    tray = Tray(num_pids=10, num_trays=10)

    assert len(tray.trays[0]) == 10
    assert list(tray.filter_visible(range(10))) == list(range(10))


def test_all_trays_are_visible_by_default():
    tray = Tray(num_pids=10, num_trays=10)
    assert tray.visible_trays == set(range(10))


def test_can_move_pids_to_tray():
    tray = Tray(num_pids=10)
    tray.move_pids_to_tray(pids={0, 1, 2}, tray=1)

    assert len(tray.trays[0]) == 7
    assert len(tray.trays[1]) == 3


def test_merge_pids_removes_other_pid():
    tray = Tray(num_pids=10)

    tray.merge_pids(0, 1)
    assert 1 not in tray.pid_to_tray
    assert len(tray.trays[0]) == 9


def test_toggle_visibility():
    tray = Tray(num_pids=10)
    tray.move_pids_to_tray(pids={0, 1, 2}, tray=1)

    assert tray.is_visible(0)
    assert tray.is_visible(3)

    tray.toggle_visibility(1)
    assert not tray.is_visible(0)

    tray.toggle_visibility(0)
    assert not tray.is_visible(3)


def test_can_get_hidden_pieces():
    tray = Tray(num_pids=9)
    tray.move_pids_to_tray([0, 1, 2], 0)
    tray.move_pids_to_tray([3, 4, 5], 1)
    tray.move_pids_to_tray([6, 7, 8], 2)
    assert tray.hidden_pieces == set()

    tray.toggle_visibility(0)
    assert tray.hidden_pieces == {0, 1, 2}

    tray.toggle_visibility(1)
    assert tray.hidden_pieces == {0, 1, 2, 3, 4, 5}

    tray.toggle_visibility(2)
    assert tray.hidden_pieces == {0, 1, 2, 3, 4, 5, 6, 7, 8}

    tray.toggle_visibility(1)
    assert tray.hidden_pieces == {0, 1, 2, 6, 7, 8}
