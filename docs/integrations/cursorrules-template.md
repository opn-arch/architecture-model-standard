# Using Architecture Model with Cursor

## Setup

1. Copy the `.cursorrules` file to your project root:
   ```bash
   cp docs/integrations/.cursorrules /path/to/your/project/.cursorrules
   ```

2. (Optional) Run the architecture model pipeline first:
   ```bash
   architecture-model init /path/to/your/project
   ```

3. Cursor will now read the `.cursorrules` file and understand your project's architecture.

## What this gives you

- Cursor's agent will check component specs before making changes
- It will respect layer boundaries and dependency directions
- It will identify which F-block a change belongs to
- It understands the model schema for updating the architecture

## Customization

Edit `.cursorrules` to add project-specific rules:
- Add naming conventions
- Specify which directories map to which layers
- Add testing requirements per component
