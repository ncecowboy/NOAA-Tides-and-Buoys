# Contributing to NOAA Tides and Buoys Integration

Thank you for your interest in contributing to this Home Assistant integration!

## Development Setup

1. Clone the repository
2. Copy the `custom_components/noaa_tides_buoys` directory to your Home Assistant's `custom_components` folder
3. Restart Home Assistant
4. Add the integration through the UI

## Code Style

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Add docstrings to all functions and classes
- Keep functions focused and small

## Testing

Before submitting a pull request:

1. Ensure all Python files compile without errors
2. Validate JSON files
3. Test the integration in a Home Assistant instance
4. Verify both tides/currents and buoy data sources work

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Versioning

This project uses [Semantic Versioning](https://semver.org/):

- MAJOR version for incompatible API changes
- MINOR version for new functionality in a backwards compatible manner
- PATCH version for backwards compatible bug fixes

## Release Process

1. Create and push a new version tag (e.g., `git tag v1.1.0 && git push --tags`)
2. Create a new GitHub release with the tag
3. The GitHub Actions workflow will automatically:
   - Update the version in `manifest.json`
   - Commit the version change back to the repository
   - Create a ZIP package for distribution

## Adding New Features

When adding new features:

- Ensure backwards compatibility when possible
- Update the README with new functionality
- Add appropriate error handling
- Consider adding new constants to `const.py`

## Questions?

Open an issue if you have questions or need help with development.
