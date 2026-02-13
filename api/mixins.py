# mixins.py
class LevelProgressionMixin:
    def needs_to_level_up(self):
        current_level = self.altrue_level
        needs_to_be_completed = current_level.get_next_level()
        if needs_to_be_completed and self.altrue_points.balance >= needs_to_be_completed.minimum_points:
            return needs_to_be_completed.level_number
        return False
