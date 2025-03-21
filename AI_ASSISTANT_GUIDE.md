# AI Assistant Guide

**IMPORTANT: READ THIS GUIDE COMPLETELY BEFORE HELPING USERS WITH THIS PROJECT**

This guide outlines the development practices and procedures to follow when assisting users with the Image Tagger project.

## Initial Setup

1. CHECK if virtual environment exists first:
   ```bash
   # Check if venv directory exists
   ls venv/
   
   # If it doesn't exist, create it:
   python -m venv venv
   pip install -r requirements.txt
   ```

2. JUST run these two commands in order:
   ```bash
   source venv/bin/activate
   python run.py --debug
   ```

## Development Best Practices

1. METHODICAL APPROACH:
   - Work on one component at a time
   - Complete and test each change before moving to the next
   - Document changes as you make them
   - Add appropriate logging statements for each significant operation
   - Review code changes before suggesting them

2. CODE ORGANIZATION:
   - Follow the established module structure
   - Keep routers focused on their specific functionality
   - Use appropriate dependencies from dependencies.py
   - Maintain consistent error handling patterns
   - Add docstrings to all new functions and classes

3. LOGGING AND DOCUMENTATION:
   - Add logging statements at appropriate levels (debug/info/error)
   - Include context in log messages (e.g., file paths, operation details)
   - Document all API endpoints in both docstrings and README
   - Keep documentation in sync with code changes
   - Update type hints and schemas as needed

4. TESTING AND VALIDATION:
   - Make small, testable changes
   - Verify each change works before proceeding
   - Let tests complete before diagnosing issues
   - Use the auto-reload feature during development
   - Test error cases and edge conditions

## Common Pitfalls to Avoid

DO NOT:
1. Modify run.py or core infrastructure without explicit request
2. Make large, sweeping changes across multiple modules
3. Ignore the established project structure
4. Skip adding logging or documentation
5. Try to "optimize" working code prematurely
6. Add new dependencies without clear justification
7. Modify test files without understanding the test suite
8. Interrupt normal startup processes

## When Things Go Wrong

1. CHECK THE LOGS:
   - Review error messages completely
   - Look for patterns in failures
   - Check log levels are appropriate
   - Verify logging context is helpful

2. SYSTEMATIC DEBUGGING:
   - Isolate the failing component
   - Review recent changes
   - Check dependencies and state
   - Verify configuration
   - Test smallest possible reproduction

3. MAKING FIXES:
   - Address root cause, not symptoms
   - Add tests for the fixed condition
   - Document why the fix works
   - Update related documentation
   - Add logging to prevent similar issues

Remember: Development should be methodical, well-documented, and focused on one task at a time. Always maintain the established patterns and practices of the project. 
