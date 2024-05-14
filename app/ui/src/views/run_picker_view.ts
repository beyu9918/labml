import {Weya as $, WeyaElement} from '../../../lib/weya/weya'
import {DataLoader} from "../components/loader"
import CACHE, {RunsFolder, RunsListCache} from "../cache/cache"
import {RunListItem, RunListItemModel} from '../models/run_list'
import {RunsListItemView} from '../components/runs_list_item'
import {SearchView} from '../components/search'
import {CancelButton} from '../components/buttons'
import {handleNetworkErrorInplace} from '../utils/redirect'
import {setTitle} from '../utils/document'
import {ScreenView} from '../screen_view'

interface RunsPickerViewOptions {
    onPicked: (run: RunListItemModel) => void
    onCancel: () => void
    title: string
    excludedRuns: Set<string>
}

export class RunsPickerView extends ScreenView {
    runListCache: RunsListCache
    currentRunsList: RunListItem[]
    elem: HTMLDivElement
    runsListContainer: HTMLDivElement
    searchQuery: string
    cancelButton: CancelButton
    private loader: DataLoader
    private readonly onPicked: (run: RunListItemModel) => void
    private readonly onCancel: () => void
    private readonly title: string
    private actualWidth: number

    constructor(opt: RunsPickerViewOptions) {
        super()

        this.onPicked = opt.onPicked
        this.onCancel = opt.onCancel
        this.title = opt.title
        this.runListCache = CACHE.getRunsList(RunsFolder.DEFAULT)

        this.cancelButton = new CancelButton({onButtonClick: this.onCancel, parent: this.constructor.name})

        this.loader = new DataLoader(async (force) => {
            let runsList = (await this.runListCache.get(force)).runs
                .filter(run => !opt.excludedRuns.has(run.run_uuid))
            this.currentRunsList = []
            for (let run of runsList) {
                this.currentRunsList.push(new RunListItem(run))
            }
        })

        this.searchQuery = ''

    }

    onResize(width: number) {
        super.onResize(width)

        this.actualWidth = Math.min(800, width)

        if (this.elem) {
            this._render().then()
        }
    }

    async _render() {
        setTitle({section: 'Runs'})
        this.elem.innerHTML = ''
        $(this.elem, $ => {
            $('div', $ => {
                $('div', $ => {
                    $('div', '.nav-container', $ => {
                        $('div', '.title', $ => {
                            $('h5', this.title)
                        })
                        $('div', '.buttons', $ => {
                            this.cancelButton.render($)
                        })
                    })
                })

                $('div', '.runs-list', $ => {
                    new SearchView({onSearch: this.onSearch}).render($)
                    this.loader.render($)
                    this.runsListContainer = $('div', '.list.runs-list.list-group', '')
                })
            })
        })

        try {
            await this.loader.load()

            this.renderList().then()
        } catch (e) {
            handleNetworkErrorInplace(e)
        }
    }

    render(): WeyaElement {
        this.elem = $('div')

        this._render().then()

        return this.elem
    }

    runsFilter = (run: RunListItemModel, query: RegExp) => {
        let name = run.name.toLowerCase()
        let comment = run.comment.toLowerCase()

        return (name.search(query) !== -1 || comment.search(query) !== -1)
    }

    onItemClicked = (elem: RunsListItemView) => {
        this.onPicked(elem.item)
    }

    onSearch = async (query: string) => {
        this.searchQuery = query
        await this.loader.load()
        this.renderList().then()
    }

    private async renderList() {
        let re = new RegExp(this.searchQuery.toLowerCase(), 'g')
        this.currentRunsList = this.currentRunsList.filter(run => this.runsFilter(run, re))

        this.runsListContainer.innerHTML = ''
        $(this.runsListContainer, $ => {
            for (let i = 0; i < this.currentRunsList.length; i++) {
                new RunsListItemView({
                    item: this.currentRunsList[i],
                    onClick: this.onItemClicked,
                    width: this.actualWidth}).render($)
            }
        })

    }
}
