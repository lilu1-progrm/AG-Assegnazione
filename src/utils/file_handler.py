import json
from pathlib import Path
from typing import Dict, Tuple, List
from models.data_models import Activity, Person

def load_data(people_file: str, activities_file: str) -> Tuple[List[Person], Dict[str, Activity]]:
    """
    Load people and activities data from JSON files.
    
    Returns:
        Tuple containing list of Person objects and dictionary of Activity objects
    """
    activities: Dict[str, Activity] = {}
    
    with open(activities_file, 'r') as f:
        activities_data = json.load(f)
        for act in activities_data:
            activities[act['name']] = Activity(
                name=act['name'],
                min_participants=act['min_participants'],
                max_participants=act['max_participants']
            )

    people: List[Person] = []
    with open(people_file, 'r') as f:
        people_data = json.load(f)
        people = [
            Person(name=person['name'], preferences=person.get('preferences', []))
            for person in people_data
        ]
    
    return people, activities

def save_results(output_dir: str, stats: dict, assignments: Dict[str, set], 
                activities: Dict[str, Activity]) -> None:
    """Save assignment results to JSON file."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    results = {
        'statistics': {
            'summary': {
                'n1': stats['n1'],
                'n2': stats['n2'],
                'n3': stats['n3'],
                'n4': stats['n4'],
                'unassigned': stats['unassigned'],
                'total_people': stats['total_people'],
                'total_activities': stats['total_activities']
            },
            'detailed_assignments': stats['detailed_assignments']
        },
        'assignments': {k: list(v) for k, v in assignments.items() if v},
        'cancelled_activities': [k for k, v in activities.items() if v.is_cancelled],
        'activity_details': {
            name: {
                'total_assigned': len(assignments[name]),
                'min_required': activity.min_participants,
                'max_allowed': activity.max_participants,
                'is_cancelled': activity.is_cancelled
            }
            for name, activity in activities.items()
        }
    }
    
    output_file = Path(output_dir) / 'assignment_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=4)