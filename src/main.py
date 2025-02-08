from core.assigner import ActivityAssigner

def main():
    assigner = ActivityAssigner()
    assigner.initialize_data('data/raw/people.json', 'data/raw/activities.json')
    assigner.assign_activities()
    assigner.save_results('results/output')

if __name__ == "__main__":
    main()