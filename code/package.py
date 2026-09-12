"""
Packaging utility to assemble code.zip for submission.
"""

import os
import zipfile

def package_submission(output_zip: str = 'code.zip'):
    print(f"Creating submission package {output_zip}...")
    
    files_to_include = [
        ('code/__init__.py', 'code/__init__.py'),
        ('code/data_loader.py', 'code/data_loader.py'),
        ('code/simulator.py', 'code/simulator.py'),
        ('code/decision_engine.py', 'code/decision_engine.py'),
        ('code/agent.py', 'code/agent.py'),
        ('code/validate_samples.py', 'code/validate_samples.py'),
        ('code/main.py', 'code/main.py'),
        ('code/package.py', 'code/package.py'),
        ('code/evaluation/usage_report.md', 'evaluation/usage_report.md'),
        ('README.md', 'README.md')
    ]

    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for src, arcname in files_to_include:
            if os.path.exists(src):
                zipf.write(src, arcname)
                print(f"  Added {src} -> {arcname}")
            else:
                print(f"  WARNING: {src} not found!")

    print(f"\nSubmission package successfully created: {output_zip} ({os.path.getsize(output_zip)} bytes)")

if __name__ == '__main__':
    package_submission()
