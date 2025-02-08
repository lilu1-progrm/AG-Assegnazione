from typing import List, Dict, Optional, Set, Tuple
from models.data_models import Activity, Person
from utils.file_handler import load_data, save_results

class ActivityAssigner:
    def __init__(self):
        self.people: List[Person] = []
        self.activities: Dict[str, Activity] = {}
        self.assignments: Dict[str, Set[str]] = {}
        self.stats = {
            'n1': 0, 'n2': 0, 'n3': 0, 'n4': 0,
            'unassigned': 0,
            'total_people': 0,
            'total_activities': 0,
            'cancelled_activities': [],
            'detailed_assignments': {
                'got_n1': [],
                'got_n2': [],
                'got_n3': [],
                'got_n4': [],
                'unassigned': []
            }
        }

    def initialize_data(self, people_file: str, activities_file: str):
        """Initialize data from files."""
        self.people, self.activities = load_data(people_file, activities_file)
        self.assignments = {name: set() for name in self.activities.keys()}
        self.stats['total_people'] = len(self.people)
        self.stats['total_activities'] = len(self.activities)

    def has_space(self, activity_name: str) -> bool:
        """Check if an activity has space for more participants."""
        if activity_name not in self.activities or self.activities[activity_name].is_cancelled:
            return False
        return len(self.assignments[activity_name]) < self.activities[activity_name].max_participants

    def assign_to_activity(self, person: Person, activity_name: str, pref_level: int) -> bool:
        """Assign a person to an activity."""
        if not self.has_space(activity_name):
            return False
            
        # Remove from previous assignment if any
        if person.assigned_activity:
            self.assignments[person.assigned_activity].remove(person.name)
            if person.preference_level is not None:
                self.stats[f'n{person.preference_level + 1}'] -= 1
                self.stats['detailed_assignments'][f'got_n{person.preference_level + 1}'].remove(person.name)

        # Assign to new activity
        self.assignments[activity_name].add(person.name)
        person.assigned_activity = activity_name
        person.preference_level = pref_level
        self.stats[f'n{pref_level + 1}'] += 1
        self.stats['detailed_assignments'][f'got_n{pref_level + 1}'].append(person.name)
        return True

    def find_best_available_activity(self, person: Person) -> Optional[Tuple[str, int]]:
        """Find the best available activity for a person without preferences."""
        best_activity = None
        smallest_gap = float('inf')
        
        for activity in self.activities.values():
            if activity.is_cancelled or not self.has_space(activity.name):
                continue
                
            current_count = len(self.assignments[activity.name])
            if current_count < activity.min_participants:
                gap = activity.min_participants - current_count
                if gap < smallest_gap:
                    smallest_gap = gap
                    best_activity = activity
            elif best_activity is None:
                if best_activity is None or current_count < len(self.assignments[best_activity.name]):
                    best_activity = activity
        
        return (best_activity.name, 0) if best_activity else None

    def optimize_assignments(self):
        """Optimize assignments to maximize N1 placements first, then N2, etc."""
        # Clear all current assignments
        for person in self.people:
            if person.assigned_activity:
                if person.preference_level is not None:
                    self.stats[f'n{person.preference_level + 1}'] -= 1
                    self.stats['detailed_assignments'][f'got_n{person.preference_level + 1}'].remove(person.name)
                self.assignments[person.assigned_activity].remove(person.name)
                person.assigned_activity = None
                person.preference_level = None

        # Process each preference level
        for pref_level in range(4):  # 0 to 3 for N1 to N4
            # Group people by their preference at this level
            activity_candidates = {}
            for person in self.people:
                if not person.assigned_activity and len(person.preferences) > pref_level:
                    activity_name = person.preferences[pref_level]
                    if not self.activities[activity_name].is_cancelled:
                        if activity_name not in activity_candidates:
                            activity_candidates[activity_name] = []
                        activity_candidates[activity_name].append(person)

            # Process each activity
            for activity_name, candidates in activity_candidates.items():
                activity = self.activities[activity_name]
                if activity.is_cancelled:
                    continue

                # Sort candidates by number of remaining preferences
                candidates.sort(key=lambda p: len(p.preferences) - pref_level)
                
                # Calculate available spaces
                available_spaces = activity.max_participants - len(self.assignments[activity_name])
                
                # Assign only up to available spaces
                for person in candidates[:available_spaces]:
                    self.assign_to_activity(person, activity_name, pref_level)

        # Handle unassigned people
        self._assign_remaining()

    def assign_activities(self):
        """Main method to assign activities to people."""
        # Initial assignment
        for person in self.people:
            if person.preferences:
                activity_name = person.preferences[0]
                if self.has_space(activity_name):
                    self.assign_to_activity(person, activity_name, 0)
            else:
                best_activity = self.find_best_available_activity(person)
                if best_activity:
                    self.assign_to_activity(person, best_activity[0], best_activity[1])

        self.optimize_assignments()

        changes_made = True
        while changes_made:
            changes_made = False
            
            potentially_cancelled = []
            for activity in self.activities.values():
                if not activity.is_cancelled:
                    count = len(self.assignments[activity.name])
                    if 0 < count < activity.min_participants:
                        potentially_cancelled.append(activity.name)
            
            for activity_name in potentially_cancelled:
                if self.try_prevent_cancellation(activity_name):
                    changes_made = True
            
            newly_cancelled = self.check_and_cancel_activities()
            if newly_cancelled:
                changes_made = True
                self._reassign_from_cancelled()

        # Final optimization
        self.optimize_assignments()

    def _reassign_from_cancelled(self):
        """Reassign people from cancelled activities."""
        unassigned = [p for p in self.people if not p.assigned_activity]
        for person in unassigned:
            if person.preferences:
                activity_name, pref_level = self.find_next_available_preference(person)
                if activity_name:
                    self.assign_to_activity(person, activity_name, pref_level)
            else:
                best_activity = self.find_best_available_activity(person)
                if best_activity:
                    self.assign_to_activity(person, best_activity[0], best_activity[1])

    def _assign_remaining(self):
        """Assign remaining unassigned people."""
        unassigned = [p for p in self.people if not p.assigned_activity]
        for person in unassigned:
            if person.preferences:
                activity_name, pref_level = self.find_next_available_preference(person)
                if activity_name:
                    self.assign_to_activity(person, activity_name, pref_level)
            else:
                best_activity = self.find_best_available_activity(person)
                if best_activity:
                    self.assign_to_activity(person, best_activity[0], best_activity[1])
                else:
                    self.stats['unassigned'] += 1
                    self.stats['detailed_assignments']['unassigned'].append(person.name)

    def check_and_cancel_activities(self) -> List[str]:
        """Check and cancel activities that don't meet minimum requirements."""
        newly_cancelled = []
        for activity in self.activities.values():
            if not activity.is_cancelled:
                current_participants = len(self.assignments[activity.name])
                if 0 < current_participants < activity.min_participants:
                    activity.is_cancelled = True
                    newly_cancelled.append(activity.name)
                    self.stats['cancelled_activities'].append(activity.name)
                    
                    for person_name in list(self.assignments[activity.name]):
                        person = next(p for p in self.people if p.name == person_name)
                        if person.preference_level is not None:
                            self.stats[f'n{person.preference_level + 1}'] -= 1
                            self.stats['detailed_assignments'][f'got_n{person.preference_level + 1}'].remove(person.name)
                        person.assigned_activity = None
                        person.preference_level = None
                    self.assignments[activity.name].clear()
        
        return newly_cancelled

    def find_next_available_preference(self, person: Person, start_pref: int = 0) -> tuple[Optional[str], Optional[int]]:
        """Find the next available preferred activity for a person."""
        for pref_idx in range(start_pref, len(person.preferences)):
            activity_name = person.preferences[pref_idx]
            if self.has_space(activity_name):
                return activity_name, pref_idx
        return None, None

    def try_prevent_cancellation(self, activity_name: str) -> bool:
        """Try to prevent an activity from being cancelled."""
        activity = self.activities[activity_name]
        needed = activity.min_participants - len(self.assignments[activity_name])
        
        for other_activity in self.activities.values():
            if other_activity.name == activity_name or other_activity.is_cancelled:
                continue
                
            current_count = len(self.assignments[other_activity.name])
            if current_count > other_activity.min_participants:
                for person_name in list(self.assignments[other_activity.name]):
                    person = next(p for p in self.people if p.name == person_name)
                    if activity_name in person.preferences:
                        new_pref_level = person.preferences.index(activity_name)
                        if self.assign_to_activity(person, activity_name, new_pref_level):
                            needed -= 1
                            if needed == 0:
                                return True
        
        return False

    def save_results(self, output_dir: str):
        """Save assignment results to file."""
        save_results(output_dir, self.stats, self.assignments, self.activities)